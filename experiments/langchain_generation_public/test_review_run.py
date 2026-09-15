import copy
import json
import pytest
from experiments.langchain_generation_public.review_run import review


def records():
    return [{"status":"started", "model_calls":2}, *[
        dict(case_id="additive",repeat=0,implementation=impl,status="returned",input_sha256="same",
            result={"candidate_response_type":"corrected_premise"}) for impl in ["baseline","langchain"]], {"status":"completed"}]


def test_old_logs_do_not_invent_raw_verdict():
    result = review(records())
    assert result["count_matches"]
    assert result["pairs"][0]["same_final_type"]
    assert all(i["type_changed"] is None for i in result["items"])


def test_raw_type_change_is_distinguished_from_model_correction():
    rows = records()
    for row, kind in zip(rows[1:3], ["answered", "corrected_premise"]):
        row["model_response_before_postprocessing"] = {"message":{"content":json.dumps({"candidate_response_type":kind})}}
    result = review(rows)
    assert [i["type_changed"] for i in result["items"]] == [True, False]


def test_incomplete_mismatched_and_duplicate_records():
    rows = records()
    assert not review(rows[:-2])["completed_marker"]
    assert not review(rows[:-2])["count_matches"]
    rows[2]["input_sha256"] = "different"
    assert not review(rows)["pairs"][0]["same_input"]
    rows.insert(2,copy.deepcopy(rows[1]))
    with pytest.raises(ValueError,match="Duplicate"):
        review(rows)
