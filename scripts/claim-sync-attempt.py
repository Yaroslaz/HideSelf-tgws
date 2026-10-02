"""Claim one upstream update before merging/building, using an atomic Git ref."""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request


def attempt_ref(tag, sha):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Unexpected upstream version tag")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Unexpected upstream commit SHA")
    return "refs/tags/hs-attempts/{}-{}".format(tag, sha)


def claim_attempt(tag, sha, base_sha, request, retry_id=None):
    ref = attempt_ref(tag, sha)
    if retry_id is not None:
        if not re.fullmatch(r"\d+-\d+", retry_id):
            raise ValueError("Invalid manual retry ID")
        ref += "-retry-" + retry_id
    payload = {"ref": ref, "sha": base_sha}
    status, _ = request("POST", "/git/refs", payload)
    if status == 201:
        return True
    if status == 422:
        # 422 can also mean an invalid request. Confirm the exact marker exists.
        status, _ = request("GET", "/git/ref/" + ref[len("refs/"):], None)
        if status == 200:
            return False
    raise RuntimeError("Could not persist the update attempt; refusing to build")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("Invalid repository")

    def request(method, path, payload):
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.github.com/repos/" + repo + path,
            data=body,
            method=method,
            headers={"Authorization": "Bearer " + token,
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, None

    base = subprocess.check_output(
        ["git", "rev-parse", "origin/" + os.environ["BASE_BRANCH"]], text=True
    ).strip()
    retry = None
    if os.environ.get("MANUAL_RETRY") == "true":
        if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
            raise ValueError("Only an explicit manual dispatch may retry")
        retry = os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
    claimed = claim_attempt(os.environ["UPSTREAM_TAG"], os.environ["UPSTREAM_SHA"],
                            base, request, retry)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("claimed={}\n".format(str(claimed).lower()))
    print("Attempt claimed before merge/build" if claimed else
          "This upstream version was already attempted; waiting for a new version or manual retry")


if __name__ == "__main__":
    main()
