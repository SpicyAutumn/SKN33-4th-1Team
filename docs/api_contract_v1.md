# 4차 프로젝트 API 통신 규칙 v1

## 1. 범위와 결정

이번 MVP의 서버 API는 다음 사용자 흐름만 우선 보장한다.

1. 회원가입·로그인·로그아웃
2. RAG 질문과 답변·출처 조회
3. 로그인 회원의 개인 검색 기록 목록·상세 조회
4. 본인의 검색 답변에 연결된 비공개 오류 제보 등록·목록·상세 조회

오늘의 이야기, 추천 주제, 문화유산 저장, 소셜 로그인, 공개 게시판과 전체 관리자 화면은 후순위다.

비회원도 RAG 검색은 사용할 수 있다. 비회원 검색 결과는 서버의 개인 검색 기록으로 저장하지 않으며, 검색 기록과 오류 제보 기능은 로그인 회원만 사용할 수 있다.

피그마에는 설명 수준이 4개로 표현되어 있지만 현재 RAG 계약은 `easy`, `general`, `advanced` 3개만 허용한다. MVP API는 구현된 3단계 계약을 유지한다. 화면 문구는 각각 `쉽게 설명`, `일반 설명`, `깊이 있게`를 사용한다.

## 2. 공통 규칙

- Base URL: `/api/v1`
- Content-Type: `application/json; charset=utf-8`
- 필드명: `snake_case`
- 시각: UTC ISO 8601 문자열. 예: `2026-09-16T08:30:00Z`
- ID: 서버가 생성한 UUID 문자열. RAG의 `request_id`, `interaction_id`, `chunk_id`는 기존 형식을 유지한다.
- 목록 정렬: 기본 `created_at DESC, id DESC`
- 페이지네이션: `cursor`와 `limit`; `limit` 기본 20, 최대 100
- 클라이언트는 `user_id`를 보내 권한을 주장하지 않는다. 서버가 인증 정보에서 현재 회원을 결정한다.
- 비공개 자원은 목록과 상세 모두 서버에서 소유권을 검사한다.
- 타인의 비공개 자원 ID로 접근하면 존재 여부를 숨기기 위해 `404 RESOURCE_NOT_FOUND`를 반환한다.
- 비밀번호, 세션 토큰, 내부 프롬프트, 전체 검색 문맥과 모델의 원시 출력은 응답·로그에 포함하지 않는다.

### 2.1 인증 기준

브라우저 MVP는 서버 세션과 `HttpOnly`, `Secure`, `SameSite=Lax` 쿠키를 사용한다. 세션 ID는 DB에 원문으로 저장하지 않고 해시만 저장한다. 상태 변경 요청에는 CSRF 방어를 적용한다. 프론트엔드가 임의의 사용자 ID를 보내는 방식은 허용하지 않는다.

### 2.2 성공 응답

단일 자원은 별도 공통 래퍼 없이 계약에 정의된 JSON 객체를 반환한다. 생성 성공은 `201 Created`, 조회·처리 성공은 `200 OK`, 로그아웃처럼 본문이 필요 없으면 `204 No Content`를 사용한다.

목록 응답은 다음 형식을 사용한다.

```json
{
  "items": [],
  "next_cursor": null
}
```

### 2.3 실패 응답

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 값을 확인해 주세요.",
    "request_id": "9be1ef27-5229-4c62-bbb2-6653a1e588f2",
    "details": [
      {"field": "question", "reason": "required"}
    ]
  }
}
```

| HTTP | 코드 | 사용 상황 |
| :--- | :--- | :--- |
| 400 | `INVALID_REQUEST` | JSON 형식 또는 요청 조합이 잘못됨 |
| 401 | `AUTHENTICATION_REQUIRED`, `INVALID_CREDENTIALS` | 로그인 필요, 로그인 실패·만료 |
| 403 | `FORBIDDEN` | 역할상 허용되지 않는 작업 |
| 404 | `RESOURCE_NOT_FOUND` | 없거나 현재 사용자가 소유하지 않은 비공개 자원 |
| 409 | `EMAIL_ALREADY_EXISTS` | 이메일 중복 등 상태 충돌 |
| 422 | `VALIDATION_ERROR` | 필드 검증 실패 |
| 429 | `RATE_LIMITED` | 호출 한도 초과 |
| 500 | `INTERNAL_ERROR` | 예상하지 못한 서버 오류 |
| 502 | `RAG_UPSTREAM_ERROR` | 검색기·생성기 호출 실패 |
| 504 | `RAG_TIMEOUT` | 모델 또는 검색 응답 시간 초과 |

화면에는 안전한 사용자 메시지만 표시하고 내부 예외·스택·비밀 값은 서버 로그의 `request_id`로 추적한다.

## 3. 회원 API

### 3.1 `POST /auth/signup`

```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "password": "user-entered-password"
}
```

- `name`: 앞뒤 공백 제거 후 1~50자
- `email`: 소문자로 정규화하며 최대 254자
- `password`: 최소 8자. DB에는 Argon2id 또는 bcrypt 해시만 저장한다.

응답 `201 Created`:

```json
{
  "id": "8bf89a61-c6e1-438a-a3b4-6f36ceff36c7",
  "name": "홍길동",
  "email": "user@example.com",
  "role": "member",
  "created_at": "2026-09-16T08:30:00Z"
}
```

### 3.2 `POST /auth/login`

요청은 `email`, `password`를 받는다. 성공 시 세션 쿠키를 설정하고 위 회원 객체를 `200 OK`로 반환한다. 이메일 존재 여부와 비밀번호 오류를 구분해 외부에 노출하지 않고 모두 `401 INVALID_CREDENTIALS`로 처리한다.

### 3.3 `POST /auth/logout`

현재 세션을 폐기하고 `204 No Content`를 반환한다.

### 3.4 `GET /auth/me`

현재 회원 객체를 반환한다. 로그인하지 않았거나 세션이 만료됐으면 `401`이다.

## 4. RAG 검색 API

### 4.1 `POST /searches`

```json
{
  "question": "경복궁은 왜 지어졌나요?",
  "audience_level": "general",
  "interaction_id": null,
  "clarification_context": null
}
```

- `question`: 필수, 공백 제거 후 1~1000자
- `audience_level`: `easy`, `general`, `advanced`
- `interaction_id`: 이어서 질문할 때만 이전 응답 값을 전달
- `clarification_context`: 기존 `0.3.0-draft` 계약 형식을 그대로 사용

응답 `200 OK`:

```json
{
  "search_record_id": "ff853978-3d77-4598-92c3-651ae1c2dc1e",
  "schema_version": "0.3.0-draft",
  "request_id": "REQ-a11c3f",
  "interaction_id": "INT-9cf21e",
  "response_type": "answered",
  "message": "경복궁은 조선 왕조의 법궁으로 지어졌습니다.",
  "audience_level": "general",
  "citations": [
    {
      "chunk_id": "aks:E0002452:...:body:0001",
      "document_id": "aks:E0002452",
      "title": "경복궁",
      "source_url": "https://encykorea.aks.ac.kr/Article/E0002452",
      "section": "body",
      "retrieval_rank": 1,
      "content": "경복궁에 관한 근거 원문 일부"
    }
  ],
  "clarification": null,
  "premise_correction": null,
  "related_topics": [],
  "warnings": [],
  "created_at": "2026-09-16T08:31:00Z"
}
```

`search_record_id`는 로그인 상태에서 저장에 성공한 경우 UUID이고, 비회원 응답에서는 `null`이다. 기존 `ServiceResponse`의 나머지 필드는 이름과 의미를 바꾸지 않는다.

검색 기록에는 답변 당시의 질문·답변·응답 유형·출처 스냅샷을 저장한다. 원문 또는 RAG 인덱스가 나중에 바뀌어도 과거 답변과 오류 제보를 재현하기 위해서다. 전체 `retrieved_contexts`나 내부 모델 출력은 저장하지 않는다.

## 5. 내 검색 기록 API

모든 엔드포인트는 로그인이 필요하다.

### 5.1 `GET /me/searches?limit=20&cursor=...`

```json
{
  "items": [
    {
      "id": "ff853978-3d77-4598-92c3-651ae1c2dc1e",
      "question": "경복궁은 왜 지어졌나요?",
      "audience_level": "general",
      "response_type": "answered",
      "answer_preview": "경복궁은 조선 왕조의 법궁으로...",
      "citation_count": 1,
      "created_at": "2026-09-16T08:31:00Z"
    }
  ],
  "next_cursor": null
}
```

### 5.2 `GET /me/searches/{search_record_id}`

`POST /searches` 성공 응답과 같은 상세 스냅샷을 반환한다. 현재 사용자의 기록이 아니면 `404`다.

검색 기록 삭제·필터·이전 답변 비교는 회의 기준 후순위이므로 v1에 넣지 않는다.

## 6. 비공개 오류 제보 API

오류 제보는 로그인 회원 자신의 `search_record_id`에만 연결할 수 있다. 답변 아래 버튼에서 진입해 질문과 답변 식별자를 자동 연결하는 흐름을 기본으로 한다.

### 6.1 `POST /me/error-reports`

```json
{
  "search_record_id": "ff853978-3d77-4598-92c3-651ae1c2dc1e",
  "category": "incorrect_fact",
  "content": "건립 연도 설명을 다시 확인해 주세요."
}
```

- `category`: `incorrect_fact`, `citation_mismatch`, `incomplete_answer`, `inappropriate_content`, `other`
- `content`: 필수, 공백 제거 후 10~2000자

응답 `201 Created`:

```json
{
  "id": "61a36ddd-06fa-4dfb-a648-6de69f08beee",
  "search_record_id": "ff853978-3d77-4598-92c3-651ae1c2dc1e",
  "category": "incorrect_fact",
  "content": "건립 연도 설명을 다시 확인해 주세요.",
  "status": "received",
  "staff_reply": null,
  "created_at": "2026-09-16T08:35:00Z",
  "updated_at": "2026-09-16T08:35:00Z"
}
```

### 6.2 `GET /me/error-reports?limit=20&cursor=...`

본인의 제보만 목록으로 반환한다. 목록 항목은 `id`, `search_record_id`, `category`, `status`, 질문 미리보기, `created_at`, `updated_at`을 포함한다.

### 6.3 `GET /me/error-reports/{report_id}`

본인의 제보 상세와 연결된 검색 질문·답변 요약을 반환한다. 타인의 제보는 `404`다.

처리 상태는 향후 확장을 위해 `received`, `reviewing`, `resolved`, `rejected`를 예약한다. 담당자용 조회·상태 변경 API, 담당자 답변과 알림은 MVP에서 제외한다. MVP에서 새 제보의 상태는 `received`로 생성한다.

## 7. 화면 상태와 API 연결

| 화면 상태 | API 결과 |
| :--- | :--- |
| 답변 대기 | 요청 진행 중. 중복 제출 방지 |
| 정상 답변 | `200`과 `answered` 또는 `corrected_premise` |
| 추가 질문 필요 | `200`과 `needs_clarification` |
| 근거 부족·범위 밖·안전 거절 | `200`과 해당 `response_type` |
| 로그인 필요 | `401 AUTHENTICATION_REQUIRED` |
| 타인 기록·제보 접근 | `404 RESOURCE_NOT_FOUND` |
| 모델 지연 | `504 RAG_TIMEOUT` |
| 검색·생성기 장애 | `502 RAG_UPSTREAM_ERROR` |

의미적 응답 유형은 HTTP 오류가 아니다. `insufficient_evidence`, `needs_clarification`, `safety_refusal`, `out_of_scope`도 서비스가 정상 판단한 결과이므로 `200`으로 반환한다.

## 8. MVP 확정 사항과 남은 기술 선택

- 비회원 검색을 허용한다. 개인 검색 기록과 오류 제보는 로그인 회원만 사용한다.
- 인증은 서버 세션과 보안 쿠키 방식으로 구현한다.
- 담당자용 제보 조회·상태 변경 기능은 MVP에서 제외한다.
- 실제 서버 구현을 시작하기 전에 API 프레임워크와 회원 데이터용 DBMS를 선택해야 한다. 현재 `db/schema_v1.sql`은 PostgreSQL 문법으로 작성된 초기안이다.
