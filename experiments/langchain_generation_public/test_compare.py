from experiments.langchain_generation_public.compare import fixture_cases, main, run_pairs


def test_capture_preserves_pre_repair_output_and_clears_between_calls():
    from experiments.langchain_generation_public.compare import ObservedGenerator
    class Repairing:
        def __init__(self):
            self.transport = lambda *args: {"message": {"content": "raw answer"}, "private_header": "secret"}
        def invoke(self, request):
            if request["question"] == "fail":
                raise ValueError("before model response")
            raw = self.transport("private-url", {}, 120)
            raw["message"]["content"] = "repaired answer"
            return raw
    wrapper = ObservedGenerator(Repairing())
    cases = fixture_cases()[:2]
    cases[1]["request"]["question"] = "fail"
    rows = run_pairs(cases, {"baseline": wrapper, "langchain": wrapper})
    assert rows[0]["model_response_before_postprocessing"]["message"]["content"] == "raw answer"
    assert "private_header" not in rows[0]["model_response_before_postprocessing"]
    assert "model_response_before_postprocessing" not in rows[2]
    assert "model_response_before_postprocessing" not in rows[3]


def test_dry_run_without_connection(monkeypatch, capsys):
    monkeypatch.delenv("LANGCHAIN_EXPERIMENT_BASE_URL", raising=False)
    assert main([]) == 0
    assert '"model_calls": 8' in capsys.readouterr().out


def test_live_requires_explicit_code_baseline(tmp_path):
    import pytest
    with pytest.raises(SystemExit) as caught:
        main(["--live", "--model", "offline", "--output", str(tmp_path / "result.jsonl")])
    assert caught.value.code == 2
    assert not (tmp_path / "result.jsonl").exists()


def test_results_are_delivered_after_each_call():
    delivered = []
    class Fake:
        def invoke(self, request):
            assert len(delivered) == self.calls
            self.calls += 1
            return {}
        calls = 0
    generator = Fake()
    rows = run_pairs(fixture_cases()[:1], {"baseline": generator, "langchain": generator}, on_record=delivered.append)
    assert delivered == rows


def test_pair_inputs_isolated_and_order_alternates():
    calls = []
    class Fake:
        def __init__(self, name): self.name = name
        def invoke(self, request):
            calls.append((self.name, request["question"]))
            request["question"] = "mutated"
            return {"ok": True}
    cases = fixture_cases()
    rows = run_pairs(cases, {n: Fake(n) for n in ["baseline", "langchain"]}, 2)
    assert len(rows) == 16
    assert [name for name, _ in calls[:4]] == ["baseline", "langchain", "langchain", "baseline"]
    assert calls[0][1] == calls[1][1]
    assert all(c["request"]["question"] != "mutated" for c in cases)
    assert rows[0]["input_sha256"] == rows[1]["input_sha256"]


def test_failure_does_not_expose_endpoint_and_other_arm_runs():
    class Fail:
        def invoke(self, request): raise RuntimeError("secret endpoint")
    class OK:
        def invoke(self, request): return {"ok": True}
    rows = run_pairs(fixture_cases()[:1], {"baseline": Fail(), "langchain": OK()})
    assert rows[0]["error_type"] == "RuntimeError"
    assert "secret" not in str(rows)
    assert rows[1]["status"] == "returned"
