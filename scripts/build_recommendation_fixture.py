"""Generate the offline UI fixture from the real catalog, without AI or DB access."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from api.network_runtime import build_network, build_network_for_question

choice = build_network_for_question("이순신에 대해 알려주세요.", ())
payload = {"choice": choice, "maps": {
    item["document_id"]: build_network(item["document_id"]) for item in choice["candidates"]}}
(root / "frontend/src/review/recommendation-fixture.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
