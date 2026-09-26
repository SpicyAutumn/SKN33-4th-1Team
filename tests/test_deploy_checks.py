"""Exercise deployment decisions offline; no GitHub or AWS requests are sent."""

import importlib.util
from pathlib import Path
import subprocess

import pytest


SPEC = importlib.util.spec_from_file_location(
    "deploy_checks", Path(__file__).parents[1] / "scripts/deploy/check_required_runs.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
SHA = "a" * 40
REPO = "owner/repo"


def run(**changes):
    return {
        "id": 10, "run_attempt": 1, "head_sha": SHA, "head_branch": "main",
        "event": "push", "head_repository": {"full_name": REPO},
        "status": "completed", "conclusion": "success", **changes,
    }


def decision(runs):
    return gate.check_run(runs, sha=SHA, repository=REPO, workflow="test.yml")


@pytest.mark.parametrize("changes", [
    {"event": "pull_request"}, {"event": "workflow_dispatch"},
    {"head_sha": "b" * 40}, {"head_branch": "feature"},
    {"head_repository": {"full_name": "fork/repo"}}, {"head_repository": None},
])
def test_other_commit_event_branch_or_repository_cannot_satisfy_gate(changes):
    assert not decision([run(**changes)])


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out", "neutral", None])
def test_latest_failure_cannot_be_hidden_by_older_success(conclusion):
    with pytest.raises(gate.CheckFailure):
        decision([run(id=20, conclusion=conclusion), run(id=10)])


def test_rerun_must_finish_and_its_latest_attempt_must_pass():
    assert not decision([run(run_attempt=2, status="in_progress", conclusion=None), run()])
    with pytest.raises(gate.CheckFailure):
        decision([run(), run(run_attempt=2, conclusion="failure")])
    assert decision([run(conclusion="failure"), run(run_attempt=2)])


class FakeGitHub:
    def __init__(self, snapshots=None, main_sha=SHA):
        self.snapshots = snapshots or {}
        self.main_sha = main_sha
        self.calls = []

    def __call__(self, endpoint):
        self.calls.append(endpoint)
        if endpoint.endswith("/git/ref/heads/main"):
            return {"object": {"sha": self.main_sha}}
        for workflow in gate.REQUIRED_WORKFLOWS:
            if f"/{workflow}/runs?" in endpoint:
                assert "event=push" in endpoint and f"head_sha={SHA}" in endpoint
                return {"workflow_runs": self.snapshots.get(workflow, [run()])}
        raise AssertionError(endpoint)


def test_all_three_checks_are_required_and_main_is_rechecked():
    api = FakeGitHub()
    gate.wait_for_checks(REPO, SHA, timeout=0, api=api)
    assert len(api.calls) == 5  # main, three workflows, main again


@pytest.mark.parametrize("workflow", gate.REQUIRED_WORKFLOWS)
def test_missing_required_workflow_blocks_manual_immediate_check(workflow):
    with pytest.raises(gate.CheckFailure, match="missing or unfinished"):
        gate.wait_for_checks(REPO, SHA, timeout=0, api=FakeGitHub({workflow: []}))


def test_waits_for_parallel_frontend_run_then_passes():
    api = FakeGitHub({"frontend-tests.yml": [run(status="in_progress", conclusion=None)]})
    ticks = [0]

    def advance(seconds):
        ticks[0] += seconds
        api.snapshots.clear()

    gate.wait_for_checks(REPO, SHA, timeout=30, interval=5, api=api, clock=lambda: ticks[0], sleep=advance)
    assert ticks[0] == 5


def test_never_waits_forever_for_absent_runs():
    api = FakeGitHub({"frontend-tests.yml": []})
    ticks = [0]

    def advance(seconds):
        ticks[0] += seconds

    with pytest.raises(gate.CheckFailure, match="missing or unfinished"):
        gate.wait_for_checks(REPO, SHA, timeout=7, interval=5, api=api, clock=lambda: ticks[0], sleep=advance)
    assert ticks[0] == 7


def test_stale_main_blocks_before_reading_checks():
    api = FakeGitHub(main_sha="b" * 40)
    with pytest.raises(gate.CheckFailure, match="main has moved"):
        gate.wait_for_checks(REPO, SHA, api=api)
    assert len(api.calls) == 1


def test_main_advancing_during_check_reads_is_rejected():
    api = FakeGitHub()

    def changing(endpoint):
        if len(api.calls) == 4:
            api.main_sha = "b" * 40
        return api(endpoint)

    with pytest.raises(gate.CheckFailure, match="main has moved"):
        gate.wait_for_checks(REPO, SHA, timeout=0, api=changing)


def test_api_failure_is_not_treated_as_success():
    def failed(endpoint):
        raise subprocess.CalledProcessError(1, ["gh", "api", endpoint])

    with pytest.raises(subprocess.CalledProcessError):
        gate.wait_for_checks(REPO, SHA, api=failed)


@pytest.mark.parametrize("repository,sha", [("bad", SHA), (REPO, "main"), (REPO, "a" * 7)])
def test_invalid_inputs_do_not_call_github(repository, sha):
    def unexpected(endpoint):
        pytest.fail("GitHub must not be called")

    with pytest.raises(ValueError):
        gate.wait_for_checks(repository, sha, api=unexpected)
