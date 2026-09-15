"""Bounded paired generation experiment. Default mode never calls a model."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def fixture_cases():
    """Synthetic facts deliberately avoid claiming historical accuracy."""
    context = dict(chunk_id="fixture:record:1", document_id="fixture:record",
        title="가상 새봄기록관", content="가상 새봄기록관은 2002년에 개관했다. 전시와 교육을 제공한다.",
        source_url="https://example.test/record", section="body", retrieval_rank=1,
        retrieval_score=0.9, score_type="similarity", metadata={})
    specs = [
        ("normal", "가상 새봄기록관은 언제 개관했어?", [context]),
        ("correction", "가상 새봄기록관은 2001년에 개관한 게 맞아?", [context]),
        ("unsupported", "가상 새봄기록관의 정확한 방문객 수는?", [context]),
        ("additive", "가상 새봄기록관은 전시뿐만 아니라 교육도 제공하는 게 맞아?", [context]),
    ]
    return [dict(case_id=name, request=dict(schema_version="0.3.0-draft",
        request_id=f"LC-{name}", interaction_id=f"LC-{name}", question=question,
        audience_level="general", response_language="ko", retrieved_contexts=contexts,
        grounding_decision="sufficient", clarification_context=None)) for name, question, contexts in specs]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class ObservedGenerator:
    """Capture model content before parsing/repair, without request URLs or headers."""
    def __init__(self, generator):
        self.generator = generator
        self.raw_model_response = None
        original_transport = generator.transport

        def observed_transport(url, payload, timeout):
            response = original_transport(url, payload, timeout)
            if isinstance(response, dict):
                self.raw_model_response = copy.deepcopy({k: response.get(k) for k in
                    ("message", "model", "done_reason", "prompt_eval_count", "eval_count")})
            return response

        generator.transport = observed_transport

    def invoke(self, request):
        self.raw_model_response = None
        return self.generator.invoke(request)


def run_pairs(cases, generators, repeats=1, on_record=None):
    records = []
    for repeat in range(repeats):
        for index, case in enumerate(cases):
            order = ["baseline", "langchain"]
            if (repeat + index) % 2:
                order.reverse()
            for position, name in enumerate(order):
                start = time.perf_counter()
                row = dict(case_id=case["case_id"], repeat=repeat, implementation=name,
                           pair_position=position, input_sha256=digest(case["request"]))
                try:
                    result = generators[name].invoke(copy.deepcopy(case["request"]))
                    row.update(status="returned", result=result)
                except Exception as exc:
                    # Exception text can contain endpoint credentials or response bodies.
                    row.update(status="error", error_type=type(exc).__name__)
                raw = getattr(generators[name], "raw_model_response", None)
                if raw is not None:
                    row["model_response_before_postprocessing"] = copy.deepcopy(raw)
                row["wall_latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
                records.append(row)
                if on_record is not None:
                    on_record(row)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Execute real model calls")
    parser.add_argument("--model", help="Explicit agreed model name")
    parser.add_argument("--expected-commit", help="Full agreed commit SHA required for live runs")
    parser.add_argument("--repeats", type=int, default=1, choices=range(1, 4))
    parser.add_argument("--output", type=Path, help="New local report file (will not overwrite)")
    args = parser.parse_args(argv)
    cases = fixture_cases()
    plan = dict(dataset="synthetic-v1", input_sha256=digest(cases),
        case_count=len(cases), model_calls=len(cases)*2*args.repeats,
        model=args.model, repeats=args.repeats, temperature=0, keep_alive="1h",
        timeout_seconds=120, quality_evaluation="manual review required",
        latency_note="No warmup; first calls may include model loading. Not a performance benchmark.")
    if not args.live:
        print(json.dumps(dict(mode="dry-run", **plan), ensure_ascii=False, indent=2))
        return 0
    if not args.model or not args.output or not args.expected_commit:
        parser.error("--live requires --model, --expected-commit and a new --output path")
    endpoint = os.environ.get("LANGCHAIN_EXPERIMENT_BASE_URL", "").strip()
    if not endpoint:
        parser.error("Set LANGCHAIN_EXPERIMENT_BASE_URL locally; .env files are not loaded")
    for name in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING"):
        os.environ[name] = "false"
    from rag_service.ollama_generator import OllamaGenerator
    from experiments.langchain_generation_public.generator import LangChainGenerator
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != args.expected_commit:
        parser.error("Current checkout does not match --expected-commit; no model calls made")
    tracked_changes = subprocess.check_output(["git", "diff", "HEAD", "--", "src/rag_service"], cwd=root)
    if tracked_changes:
        parser.error("Generation/service code has local changes; establish a clean baseline before live runs")
    source_hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__), Path(__file__).with_name("generator.py"),
                     root / "src/rag_service/ollama_generator.py"]}
    # Reserve output before making any paid/network calls; existing files are never overwritten.
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(status="started", commit=commit, source_hashes=source_hashes, **plan), ensure_ascii=False)+"\n")
        stream.flush()
        generators = {name: ObservedGenerator(cls(base_url=endpoint, model=args.model, keep_alive="1h"))
            for name, cls in [("baseline", OllamaGenerator), ("langchain", LangChainGenerator)]}
        def save_row(row):
            stream.write(json.dumps(row, ensure_ascii=False)+"\n")
            stream.flush()
            print(f"{row['case_id']} / {row['implementation']}: {row['status']}", flush=True)
        run_pairs(cases, generators, args.repeats, on_record=save_row)
        stream.write(json.dumps({"status": "completed"})+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
