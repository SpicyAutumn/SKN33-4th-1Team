"""Read-only catalog exploration; no login, DB write, or model invocation."""
import re

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .network_runtime import HeritageNetworkUnavailableError, build_network, build_network_for_question

DOCUMENT_ID = re.compile(r"aks:[A-Za-z0-9_-]{1,64}")


def _error(code, message, status):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


@require_GET
def heritage_network(request):
    document_id = request.GET.get("document_id", "").strip()
    question = request.GET.get("question", "").strip()
    raw_ids = request.GET.get("document_ids", "")
    ids = tuple(value.strip() for value in raw_ids.split(",") if value.strip())
    if (len(question) > 500 or len(ids) > 10
            or any(not DOCUMENT_ID.fullmatch(value) for value in ids)
            or (document_id and (question or ids))
            or (document_id and not DOCUMENT_ID.fullmatch(document_id))
            or not (document_id or question or ids)):
        return _error("VALIDATION_ERROR", "질문 또는 문화유산 문서 ID를 확인해 주세요.", 422)
    try:
        payload = build_network(document_id) if document_id else build_network_for_question(question, ids)
    except HeritageNetworkUnavailableError:
        return _error("NETWORK_UNAVAILABLE", "연관 문화유산을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", 503)
    if payload is None:
        return _error("RESOURCE_NOT_FOUND", "연결 정보를 찾지 못했습니다. 질문에 문화유산 이름을 포함해 주세요.", 404)
    return JsonResponse(payload)
