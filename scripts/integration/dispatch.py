"""Trusted GitHub Actions controller for the common integration test site."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


MARKER = "<!-- heritage-integration-test -->"
SHA = re.compile(r"[0-9a-f]{40}")
INSTANCE = re.compile(r"i-[0-9a-f]+")


def github(path: str, method: str = "GET", body: dict | None = None):
    request = urllib.request.Request(
        "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"] + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def selected_prs() -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for page in range(1, 11):
        pulls = github(f"/pulls?state=open&base=main&per_page=100&page={page}")
        for pr in pulls:
            same_repository = (pr.get("head", {}).get("repo") or {}).get("full_name") == os.environ["GITHUB_REPOSITORY"]
            labeled = any(label.get("name") == "preview" for label in pr.get("labels", []))
            if same_repository and labeled and isinstance(pr.get("number"), int) and SHA.fullmatch(pr.get("head", {}).get("sha", "")):
                selected.append({"number": pr["number"], "sha": pr["head"]["sha"]})
        if len(pulls) < 100:
            break
    return sorted(selected, key=lambda pr: pr["number"])


def aws(*args: str) -> dict:
    return json.loads(subprocess.check_output(["aws", "ssm", *args, "--output", "json"], text=True))


def upsert_comment(number: int, body: str) -> None:
    comment = None
    for page in range(1, 11):
        comments = github(f"/issues/{number}/comments?per_page=100&page={page}")
        comment = next((item for item in comments if item.get("user", {}).get("login") == "github-actions[bot]"
                        and item.get("body", "").startswith(MARKER)), None)
        if comment or len(comments) < 100:
            break
    if comment:
        github(f"/issues/comments/{comment['id']}", "PATCH", {"body": body})
    else:
        github(f"/issues/{number}/comments", "POST", {"body": body})


def main() -> None:
    instance = os.environ["TEST_INSTANCE_ID"]
    production = os.environ.get("PRODUCTION_INSTANCE_ID", "")
    if not INSTANCE.fullmatch(instance) or instance == production:
        raise RuntimeError("The integration deployment must target its dedicated EC2 instance")
    main_sha = github("/git/ref/heads/main")["object"]["sha"]
    if not SHA.fullmatch(main_sha):
        raise RuntimeError("Could not resolve the current main commit")
    prs = selected_prs()
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    changed_pr = event.get("number")
    payload = base64.b64encode(json.dumps({"main_sha": main_sha, "prs": prs}).encode()).decode()
    server = base64.b64encode(Path("scripts/integration/server.py").read_bytes()).decode()
    bootstrap = base64.b64encode(Path("scripts/integration/bootstrap_db.py").read_bytes()).decode()
    remote = f'''set -eu
work=$(mktemp -d /tmp/heritage-integration.XXXXXX)
trap 'rm -rf "$work"' EXIT
printf '%s' '{server}' | base64 -d > "$work/server.py"
printf '%s' '{bootstrap}' | base64 -d > "$work/bootstrap_db.py"
chmod 644 "$work/server.py" "$work/bootstrap_db.py"
sudo -u ubuntu -H python3 "$work/server.py" '{payload}'
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as parameters:
        json.dump({"commands": [remote], "executionTimeout": ["2400"]}, parameters)
        parameters.flush()
        response = aws("send-command", "--instance-ids", instance, "--document-name", "AWS-RunShellScript",
                       "--timeout-seconds", "120", "--parameters", "file://" + parameters.name,
                       "--comment", "Reconcile common integration test site")
    command_id = response["Command"]["CommandId"]
    print(f"SSM command: {command_id}", flush=True)
    for _ in range(252):
        completed = subprocess.run(
            ["aws", "ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", instance,
             "--output", "json"], text=True, capture_output=True,
        )
        if completed.returncode:
            if "InvocationDoesNotExist" in completed.stderr:
                time.sleep(10)
                continue
            raise RuntimeError(completed.stderr)
        result = json.loads(completed.stdout)
        if result["Status"] in ("Pending", "InProgress", "Delayed"):
            time.sleep(10)
            continue
        if result["Status"] != "Success":
            raise RuntimeError(f"Integration deployment failed ({result['Status']}); inspect SSM command {command_id}.")
        record = next((json.loads(line.removeprefix("INTEGRATION_RESULT=")) for line in result["StandardOutputContent"].splitlines()
                       if line.startswith("INTEGRATION_RESULT=")), None)
        if not record:
            raise RuntimeError(f"Integration result was missing; inspect SSM command {command_id}.")
        url = record["url"]
        if record["state"] == "ready":
            included = ", ".join(f"#{number}" for number in record["prs"])
            message = (f"{MARKER}\n공용 통합 테스트 반영 완료: {url}\n\n"
                       f"포함 PR: {included}\n기준 main: `{record['main_sha'][:12]}`\n"
                       "이 사이트의 DB는 테스트 전용이며, 다음 통합 배포 때 초기화됩니다.")
            for number in record["prs"]:
                upsert_comment(number, message)
        else:
            message = f"{MARKER}\n`preview` 라벨이 붙은 PR이 없어 공용 통합 테스트 사이트를 중지했습니다."
        if isinstance(changed_pr, int) and changed_pr not in record.get("prs", []):
            upsert_comment(
                changed_pr,
                f"{MARKER}\n이 PR은 현재 공용 통합 테스트 대상에서 제외되었습니다. "
                "`preview` 라벨을 다시 붙이면 다음 통합 배포에 포함됩니다.",
            )
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(message + "\n", encoding="utf-8")
        print(message)
        return
    raise TimeoutError(f"Inspect SSM command {command_id}; it may still be running.")


if __name__ == "__main__":
    main()
