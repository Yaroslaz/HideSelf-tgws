import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

spec = importlib.util.spec_from_file_location(
    "sync_attempt", Path(__file__).parents[1] / "scripts" / "claim-sync-attempt.py")
sync_attempt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_attempt)


class SyncAttemptTests(unittest.TestCase):
    def test_release_push_updates_branch_and_tag_together_or_neither(self):
        workflow = (Path(__file__).parents[1] / ".github/workflows/sync-upstream.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Push main and release tag\n", 1)[1]
        block = block.split("      - name:", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        bash = (r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash"))
        with tempfile.TemporaryDirectory(prefix="hideself-release-test-") as directory:
            remote = Path(directory) / "remote.git"
            local = Path(directory) / "local"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", str(local)], check=True, capture_output=True)

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=local,
                                               stderr=subprocess.STDOUT, text=True).strip()

            git("config", "user.name", "Workflow test")
            git("config", "user.email", "test@example.invalid")
            git("config", "commit.gpgsign", "false")
            git("config", "tag.gpgsign", "false")
            git("checkout", "-b", "main")
            git("commit", "--allow-empty", "-m", "initial")
            git("remote", "add", "origin", str(remote))
            git("push", "origin", "main")
            git("commit", "--allow-empty", "-m", "new runtime")
            shell_file = local / "publish.sh"

            def publish(tag):
                shell_file.write_text(script.replace("${{ steps.hs-tag.outputs.next_tag }}", tag)
                                      .replace("${{ steps.resolve.outputs.latest_tag }}", "v1.10.4"),
                                      encoding="utf-8", newline="\n")
                return subprocess.run([bash, shell_file.as_posix()], cwd=local,
                                      env=dict(os.environ, BASE_BRANCH="main"),
                                      capture_output=True, text=True)

            result = publish("v1.0.0-hs.26")
            self.assertEqual(result.returncode, 0, result.stderr)
            published = git("rev-parse", "HEAD")
            remote_refs = git("ls-remote", "origin", "refs/heads/main", "refs/tags/v1.0.0-hs.26^{}")
            self.assertEqual([line.split()[0] for line in remote_refs.splitlines()], [published, published])

            # Another writer advances main while this run prepares its tag.
            git("commit", "--allow-empty", "-m", "pending release")
            git("checkout", "-b", "racer", published)
            git("commit", "--allow-empty", "-m", "concurrent main update")
            raced = git("rev-parse", "HEAD")
            git("push", "origin", "racer:main")
            git("checkout", "main")
            self.assertNotEqual(publish("v1.0.0-hs.27").returncode, 0)
            self.assertEqual(git("ls-remote", "origin", "refs/heads/main").split()[0], raced)
            self.assertEqual(git("ls-remote", "origin", "refs/tags/v1.0.0-hs.27"), "")

    def test_workflow_plan_including_manual_retry_after_pushed_failed_build_tag(self):
        # Execute the actual workflow resolver, rather than a copied predicate.
        workflow = (Path(__file__).parents[1] / ".github/workflows/sync-upstream.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Resolve latest upstream tag\n", 1)[1]
        block = block.split("      - name:", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        bash = (r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash"))
        with tempfile.TemporaryDirectory(prefix="hideself-sync-test-") as directory:
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=directory,
                                               stderr=subprocess.STDOUT, text=True).strip()
            git("init")
            git("config", "user.name", "Workflow test")
            git("config", "user.email", "test@example.invalid")
            git("config", "commit.gpgsign", "false")
            git("commit", "--allow-empty", "-m", "old fork")
            old = git("rev-parse", "HEAD")
            git("tag", "v1.0.0-hs.25")
            git("commit", "--allow-empty", "-m", "upstream")
            new = git("rev-parse", "HEAD")
            git("tag", "v1.10.4")
            shell_file = Path(directory) / "resolve.sh"
            shell_file.write_text(script, encoding="utf-8", newline="\n")
            output = Path(directory) / "outputs"

            def plan(base, retry="false"):
                git("update-ref", "refs/remotes/origin/main", base)
                output.write_text("", encoding="utf-8")
                env = dict(os.environ, HS_TAG_PREFIX="v1.0.0-hs.", BASE_BRANCH="main",
                           MANUAL_RETRY=retry, GITHUB_OUTPUT=output.as_posix())
                subprocess.run([bash, shell_file.as_posix()], cwd=directory, env=env,
                               check=True, capture_output=True, text=True)
                return dict(line.split("=", 1) for line in output.read_text().splitlines())

            self.assertEqual(plan(old)["merge_needed"], "true")
            self.assertEqual(plan(new)["update_needed"], "true")
            git("tag", "v1.0.0-hs.26", new)
            self.assertEqual(plan(new)["update_needed"], "false")
            self.assertEqual(plan(new, "true")["update_needed"], "true")

    def test_failed_merge_or_build_does_not_grant_another_attempt(self):
        markers = set()

        def request(method, path, payload):
            if method == "POST":
                ref = payload["ref"]
                if ref in markers:
                    return 422, None
                markers.add(ref)
                return 201, None
            return (200 if "refs/" + path[len("/git/ref/"):] in markers else 404), None

        claim = lambda tag, sha, retry=None: sync_attempt.claim_attempt(
            tag, sha, "c" * 40, request, retry)
        self.assertTrue(claim("v1.10.4", "a" * 40))
        # The claim persists regardless of what happens after it, and a second
        # caller cannot acquire the same version concurrently.
        self.assertFalse(claim("v1.10.4", "a" * 40))
        self.assertTrue(claim("v1.10.5", "b" * 40))
        self.assertTrue(claim("v1.10.4", "a" * 40, "100-1"))
        self.assertFalse(claim("v1.10.4", "a" * 40, "100-1"))

    def test_invalid_or_unpersisted_claim_never_allows_build(self):
        with self.assertRaises(RuntimeError):
            sync_attempt.claim_attempt("v1.10.4", "a" * 40, "c" * 40,
                                       lambda *args: (403, None))
        with self.assertRaises(RuntimeError):
            sync_attempt.claim_attempt("v1.10.4", "a" * 40, "c" * 40,
                                       lambda *args: (422 if args[0] == "POST" else 404, None))
        with self.assertRaises(ValueError):
            sync_attempt.attempt_ref("v1.10.4; arbitrary", "a" * 40)
