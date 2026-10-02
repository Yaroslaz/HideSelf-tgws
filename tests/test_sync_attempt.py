import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "sync_attempt", Path(__file__).parents[1] / "scripts" / "claim-sync-attempt.py")
sync_attempt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_attempt)


class SyncAttemptTests(unittest.TestCase):
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
