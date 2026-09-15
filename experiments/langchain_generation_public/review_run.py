"""Review paired local results without model calls or automatic fact judgements."""
import argparse
import json
from pathlib import Path


def review(rows):
    if not rows or rows[0].get("status") != "started":
        raise ValueError("Missing run header")
    seen, items = set(), []
    for row in rows[1:]:
        if "case_id" not in row:
            continue
        key = (row["case_id"], row["repeat"], row["implementation"])
        if key in seen:
            raise ValueError("Duplicate case/repeat/implementation")
        seen.add(key)
        raw = row.get("model_response_before_postprocessing")
        raw_type, raw_status = None, "not_recorded"
        if raw is not None:
            try:
                content = raw["message"]["content"].strip()
                if content.startswith("```"):
                    content = "\n".join(content.splitlines()[1:-1])
                parsed = json.loads(content)
                raw_type = parsed.get("candidate_response_type")
                raw_status = "parsed" if isinstance(raw_type, str) else "type_missing"
            except (KeyError, TypeError, ValueError, AttributeError):
                raw_status = "unparseable"
        result = row.get("result", {})
        final_type = result.get("candidate_response_type")
        items.append(dict(case_id=row["case_id"], repeat=row["repeat"],
            implementation=row["implementation"], status=row["status"],
            raw_status=raw_status, raw_type=raw_type, final_type=final_type,
            type_changed=(raw_type != final_type) if raw_status == "parsed" and final_type else None,
            input_sha256=row.get("input_sha256"),
            content_review="human_review_required"))
    groups = {}
    for item in items:
        groups.setdefault((item["case_id"], item["repeat"]), {})[item["implementation"]] = item
    pairs = []
    for (case_id, repeat), group in groups.items():
        a, b = group.get("baseline"), group.get("langchain")
        paired = a is not None and b is not None
        pairs.append(dict(case_id=case_id, repeat=repeat, both_present=paired,
            same_input=(bool(a["input_sha256"]) and a["input_sha256"] == b["input_sha256"]) if paired else None,
            same_final_type=(a["final_type"] == b["final_type"]) if paired and a["status"] == b["status"] == "returned" else None))
    return dict(completed_marker=rows[-1].get("status") == "completed",
        expected_calls=rows[0].get("model_calls"), recorded_calls=len(items),
        count_matches=len(items) == rows[0].get("model_calls"), items=items, pairs=pairs,
        warning="Type agreement is not factual accuracy. Missing raw output cannot establish error origin.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = review([json.loads(line) for line in args.input.read_text(encoding="utf-8-sig").splitlines() if line.strip()])
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(f"Recorded {result['recorded_calls']}/{result['expected_calls']}; completed={result['completed_marker']}")
