"""Require successful checks for the current main commit before AWS deployment."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from urllib.parse import urlencode


REQUIRED_WORKFLOWS = (
    "python-tests.yml",
    "frontend-tests.yml",
    "heritage-network-check.yml",
)


class CheckFailure(RuntimeError):
    """The requested commit must not be deployed."""


def github_api(endpoint: str) -> dict:
    result = subprocess.run(
        ["gh", "api", endpoint], check=True, capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)


def check_run(runs: list[dict], *, sha: str, repository: str, workflow: str) -> bool:
    """Ignore PR/other-commit runs; a newer failure must override an older success."""
    candidates = [
        run for run in runs
        if run.get("head_sha") == sha
        and run.get("head_branch") == "main"
        and run.get("event") == "push"
        and (run.get("head_repository") or {}).get("full_name") == repository
    ]
    if not candidates:
        return False
    latest = max(candidates, key=lambda run: (run["id"], run.get("run_attempt", 1)))
    if latest.get("status") != "completed":
        return False
    if latest.get("conclusion") != "success":
        raise CheckFailure(f"{workflow}: latest main push run concluded {latest.get('conclusion')}")
    return True


def wait_for_checks(
    repository: str, sha: str, *, timeout: float = 900, interval: float = 15,
    api=github_api, clock=time.monotonic, sleep=time.sleep,
) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Expected a full commit SHA")
    if timeout < 0 or interval <= 0:
        raise ValueError("Invalid timeout or interval")
    deadline = clock() + timeout
    previous = None
    query = urlencode({"branch": "main", "event": "push", "head_sha": sha, "per_page": 100})
    while True:
        if api(f"repos/{repository}/git/ref/heads/main")["object"]["sha"] != sha:
            raise CheckFailure("main has moved; refusing stale deployment")
        waiting = []
        for workflow in REQUIRED_WORKFLOWS:
            response = api(f"repos/{repository}/actions/workflows/{workflow}/runs?{query}")
            if not check_run(response["workflow_runs"], sha=sha, repository=repository, workflow=workflow):
                waiting.append(workflow)
        if not waiting:
            # main may have advanced while the individual run results were read.
            if api(f"repos/{repository}/git/ref/heads/main")["object"]["sha"] != sha:
                raise CheckFailure("main has moved; refusing stale deployment")
            print(f"All required main push checks passed for {sha}", flush=True)
            return
        if clock() >= deadline:
            raise CheckFailure("Required checks missing or unfinished: " + ", ".join(waiting))
        if waiting != previous:
            print("Waiting for: " + ", ".join(waiting), flush=True)
            previous = waiting
        sleep(min(interval, max(0, deadline - clock())))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    try:
        wait_for_checks(os.environ["GITHUB_REPOSITORY"], args.sha, timeout=args.timeout)
    except (CheckFailure, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Deployment checks failed: {error}\n")


if __name__ == "__main__":
    main()
