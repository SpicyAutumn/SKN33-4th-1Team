# Heritage Guide API 명세 (현재 구현)

기준: `backend/api/urls.py`, `backend/api/views.py`, `backend/api/search_links.py`, `backend/api/network_views.py`의 현재 구현. 모든 경로는 `/api` 접두사를 포함하며 JSON을 받는 요청은 `Content-Type: application/json`을 사용한다. 로그인 사용자 API는 `heritage_session` 쿠키로 인증한다. 브라우저의 상태 변경 요청은 먼저 `GET /api/v1/auth/csrf`를 호출하고 `X-CSRFToken` 헤더를 보내야 한다. 관리자 API는 `heritage_admin_session` 쿠키를 사용한다.

오류 응답은 일반적으로 `{"error":{"code":"...","message":"..."}}` 형식이다. 입력 형식 오류는 400, 인증 실패는 401, 권한 또는 리소스 없음은 404, 규칙 위반은 422, 이미 사용 중인 이메일은 409, 상위 RAG 서비스 장애는 502, 연관망 서비스 장애는 503을 반환한다. Django CSRF 거부와 라우트/HTTP 메서드 불일치는 프레임워크 응답일 수 있어 이 JSON 형식이 보장되지 않는다.

## 인증 및 프로필

| 메서드·경로 | 접근 | 요청·응답 요약 |
|---|---|---|
| `GET /api/health` | 공개 | 상태, API 버전, 미디어 카탈로그 상태 |
| `GET /api/v1/auth/csrf` | 공개 | `csrf_token`; CSRF 쿠키도 설정 |
| `POST /api/v1/auth/signup` | 공개 | `{name,email,password}`; 성공 201 및 사용자 정보와 세션 쿠키 |
| `POST /api/v1/auth/login` | 공개 | `{email,password}`; 사용자 정보와 세션 쿠키 |
| `POST /api/v1/auth/logout` | 세션 선택 | 세션 폐기 및 쿠키 제거; 204 |
| `GET /api/v1/auth/me` | 로그인 | 사용자 정보 |
| `GET /api/v1/me` | 로그인 | 현재 사용자 정보 |
| `PATCH /api/v1/me` | 로그인 | `{name,email,current_password?}`; 이메일 변경 시 현재 비밀번호 필요; 사용자 정보 |
| `DELETE /api/v1/me` | 로그인 | `{current_password,confirmation:"탈퇴"}`; 계정 및 개인 데이터 삭제; 204 |
| `POST /api/v1/me/password` | 로그인 | `{current_password,new_password}`; 새 비밀번호는 8자 이상 |

사용자 응답은 `{id,name,email,role,created_at}`이다. 비밀번호는 일반 오류 제보 입력처럼 JSON 객체가 아닌 배열·숫자·null이거나 JSON 파싱이 실패하면 `INVALID_REQUEST` 400으로 거절한다.

## 질문·검색 결과

| 메서드·경로 | 접근 | 요청·응답 요약 |
|---|---|---|
| `POST /api/v1/searches` | 공개, 로그인 시 기록 저장 | `{question,audience_level?,interaction_id?,clarification_context?,selected_source_chunk_ids?}`; 질문 최대 1,000자, 난이도 `easy/general/advanced`, 추가 근거 최대 3개 |
| `GET /api/v1/searches/{result_id}` | 소유 계정 또는 검색한 비로그인 브라우저 | 저장 답변 스냅샷 반환. 결과 UUID는 경로에서 검사 |
| `POST /api/v1/searches/{result_id}/share` | 소유자 | 공개 공유 경로 발급. CSRF 필요 |
| `GET /api/v1/shared-searches/{share_token}` | 공개 | 명시적으로 공유된 답변만 반환 |
| `GET /api/v1/me/searches?limit=20` | 로그인 | 상세 검색 기록 목록. `limit`는 1~100으로 보정, 기본 20; `next_cursor`는 현재 항상 `null` |
| `GET /api/v1/me/searches/{record_id}` | 로그인, 본인 기록 | 검색 상세와 인용 반환; UUID 경로 |
| `GET /api/v1/heritage-network?document_id=...` | 공개 | 문서 ID 기준 연관망 |
| `GET /api/v1/heritage-network?question=...&document_ids=...` | 공개 | 질문/문서 ID 기준 연관망; 질문 최대 500자, 문서 ID 최대 10개 |

검색 응답은 RAG 답변 필드에 `search_result_id`, `created_at`, `share_path`를 추가한다. 비로그인 개인 결과는 해당 브라우저의 HttpOnly 쿠키로 보호한다. 공유 결과에는 내부 요청·대화 ID를 포함하지 않는다.

## 오류 제보

유형 코드는 `incorrect_fact`, `citation_mismatch`, `incomplete_answer`, `inappropriate_content`, `other`이다. 여러 유형을 선택할 수 있다. 예전 단일 선택 클라이언트의 `category` 필드도 계속 받는다. 응답은 호환을 위해 첫 유형을 `category`로, 전체를 `categories` 배열로 돌려준다.

| 메서드·경로 | 접근 | 요청·응답 요약 |
|---|---|---|
| `GET /api/v1/me/error-reports` | 로그인 | 본인 제보 최대 20개, `next_cursor:null`; 목록에는 `categories` 포함 |
| `POST /api/v1/me/error-reports` | 로그인 | 아래 요청 구조; 성공 201 및 상세 제보 |
| `GET /api/v1/me/error-reports/{report_id}` | 로그인, 본인 제보 | 제보 상세와 선택 문구 |
| `GET /api/v1/admin/error-reports?status=all` | 관리자 | 최대 100개. status는 `all/received/reviewing/completed` |
| `GET /api/v1/admin/error-reports/{report_id}` | 관리자 | 제보, 전체 유형, 선택 문구, 당시 질문·답변 |
| `PATCH /api/v1/admin/error-reports/{report_id}` | 관리자 | `{status,staff_reply}`. 완료 상태에는 10자 이상 답변 필요, 최대 2,000자 |

제보 요청 예시:

```json
{
  "search_record_id": "00000000-0000-4000-8000-000000000000",
  "categories": ["incorrect_fact", "citation_mismatch"],
  "content": "추가 설명은 선택 문구가 있으면 비워 둘 수 있습니다.",
  "selected_quotes": [
    {"text": "답변에서 선택한 문장", "start_offset": 12, "end_offset": 25}
  ]
}
```

`selected_quotes`는 생략 가능하며 최대 5개다. 각 항목은 답변에 실제 포함된 비어 있지 않은 `text`(최대 2,000자)여야 한다. offset은 둘 다 생략하거나 둘 다 제공해야 한다. 제공하면 0 이상의 정수 범위가 답변의 동일 문구를 가리켜야 한다. 기타 유형이 선택됐거나 선택 문구가 하나도 없으면 추가 설명은 10~2,000자가 필요하다. 유형 없음, 잘못된 인용, 잘못된 검색 기록 UUID는 422를 돌려준다. 존재하지 않거나 타인 소유인 유효 UUID는 404다.

## 관리자 대시보드

| 메서드·경로 | 접근 | 동작 |
|---|---|---|
| `GET /api/v1/admin/session` | 공개 | 관리자 세션 인증 여부 |
| `POST /api/v1/admin/login` | 공개 | `{password}`; 설정된 운영자 비밀번호 검증 후 관리자 쿠키 설정 |
| `POST /api/v1/admin/logout` | 공개 | 관리자 쿠키 제거; 204 |
| `GET /api/v1/admin/dashboard` | 관리자 | 집계, 최근 제보 최대 6건, 최근 로그인 사용자 최대 6명, 최근 검색 최대 10건 |
| `GET /api/v1/admin/users?limit=20&offset=0` | 관리자 | 활성 세션 기준 사용자 목록; limit 1~100, offset 0 이상, `total` 포함 |
| `GET /api/v1/admin/searches?limit=20&offset=0` | 관리자 | 검색 목록; limit 1~100, offset 0 이상, `total` 포함 |
| `GET /api/v1/admin/searches/{record_id}` | 관리자 | 검색 상세, 인용, 미디어 정보 |

## 현재 페이지 처리와 제한

기존 목록 API는 커서 기반 페이지 이동을 아직 구현하지 않았다. 사용자 검색은 기본 20/최대 100이며 응답의 `next_cursor`는 늘 `null`; 사용자 제보는 최근 20건 고정이며 `next_cursor:null`; 관리자 제보는 최대 100건 고정이다. 관리자 사용자/검색만 `limit`와 `offset`을 쓴다. 100건이 넘는 관리자 제보/검색 기록을 계속 넘겨 보는 계약은 없으므로, 클라이언트는 전체 데이터가 온다고 가정하면 안 된다.

## 관련 문서

- [검색 결과 링크 동작 및 공유](../SEARCH_RESULT_LINKS.md)
- [오류 제보 화면의 최신 구현 계약과 과거 시안 구분](../ERROR_REPORT_UI_SPEC.md)
- OpenAPI/Swagger 기계 판독 문서는 아직 생성하지 않았다. 이 문서는 코드 기준의 사람용 명세다.
