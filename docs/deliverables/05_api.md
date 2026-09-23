# API 명세서

## 1. 공통 규칙

API는 화면과 서버가 요청·응답을 주고받는 규칙이다. 아래 경로는 모두 `/api`로 시작하며 끝에 슬래시를 붙이지 않는다. `{id}`와 `{token}`은 UUID 형식의 식별자이다. 경로별 전체 필드와 예시는 [상세 API 명세](../api/API_SPEC.md)에 정리되어 있다.

- 읽기는 주로 GET, 생성·처리는 POST, 일부 변경은 PATCH, 탈퇴는 DELETE를 사용한다.
- 회원 인증은 쿠키 기반이다. 변경 요청에는 CSRF 방어 설정을 따른다. CSRF는 다른 사이트가 사용자를 대신해 변경 요청을 보내는 것을 막기 위한 확인이다.
- 개인 결과 접근과 공개 공유 링크 접근은 별개이다.
- 아래 표는 URL·메서드·주요 입력·권한을 한눈에 비교하기 위한 요약이다.

## 2. 상태·인증·회원

| 메서드 | 경로 | 목적·주요 입력 | 권한 |
|---|---|---|---|
| GET | /health | 서비스 상태 확인 | 공개 |
| GET | /v1/auth/csrf | CSRF 토큰 준비 | 공개 |
| POST | /v1/auth/signup | name, email, password | 공개 |
| POST | /v1/auth/login | email, password | 공개 |
| POST | /v1/auth/logout | 현재 로그인 종료 | 로그인하지 않아도 호출 가능 |
| GET | /v1/auth/me | 로그인 사용자 확인 | 회원 |
| GET | /v1/me | 내 정보 조회 | 회원 |
| PATCH | /v1/me | name, email; 이메일 변경 시 current_password | 회원 |
| DELETE | /v1/me | current_password, confirmation="탈퇴" | 회원 |
| POST | /v1/me/password | current_password, new_password | 회원 |

비밀번호 변경 시 현재 세션 외 다른 세션을 무효화하는 코드가 있다. 탈퇴는 실제 데이터 삭제를 포함하므로 통합 시험에서는 전용 계정만 사용한다.

## 3. 질문·기록·공유·추천

| 메서드 | 경로 | 목적·주요 입력 | 권한 |
|---|---|---|---|
| POST | /v1/searches | question, audience_level, 선택적 추가 질문 문맥 | 공개·회원 |
| GET | /v1/searches/{id} | 개인 결과 재조회 | 소유 회원 또는 비회원 쿠키 |
| POST | /v1/searches/{id}/share | 공유 링크 발급 | 개인 결과 소유권 확인 |
| GET | /v1/shared-searches/{token} | 공개 결과 조회 | 링크 보유자 |
| GET | /v1/me/searches | 회원 검색 기록; limit | 회원 본인 |
| GET | /v1/me/searches/{id} | 회원 기록 상세 | 회원 본인 |
| GET | /v1/heritage-network | document_id 또는 question/document_ids | 공개 |

### 질문 입력

```json
{
  "question": "경복궁 근정전은 어떤 곳인가요?",
  "audience_level": "general"
}
```

위 JSON은 **요청 형식 예시**이며 실행 결과가 아니다.

| 필드 | 조건 |
|---|---|
| question | 앞뒤 공백 제거 후 1~1,000자 |
| audience_level | easy / general / advanced; 생략 시 general |
| interaction_id | 제공 시 공백이 아닌 문자열 |
| clarification_context | 제공 시 객체 |
| selected_source_chunk_ids | 최대 3개, 각 1~512자; 사용 시 위 두 문맥 필드 필요 |

현재 화면의 수준 표시는 easy=초등학생, general=중·고등학생, advanced=성인 일반이다. 코드값 advanced를 “전문가 수준”으로 임의 번역하지 않는다.

### 결과·공유 응답

| 항목 | 의미 |
|---|---|
| response_type | 답변·보류 등 처리 유형 |
| message, summary | 본문·요약; 과거 기록에는 요약이 없을 수 있음 |
| citations, media | 근거·사진 |
| clarification, premise_correction, warnings | 추가 확인·전제 정정·주의 정보 |
| search_result_id, created_at, share_path | 개인 결과 ID·시각·공유 경로 |

공유 발급은 `share_path`를 반환한다. 공개 결과는 내부 request_id·interaction_id와 개인 결과 식별 정보를 제외하는 허용 목록을 사용한다. 공개 질문·본문 자체에 개인정보가 없는지도 별도 시험해야 한다.

비회원 개인 결과는 검색 당시 브라우저 쿠키가 필요하며 유효기간은 비회원 검색마다 30일로 갱신된다. 쿠키를 잃으면 개인 주소 접근이 불가능하다. 현재 공유 취소·만료는 구현 범위 밖이다.

회원 기록 목록은 limit 기본 20·최대 100이며 `next_cursor=null`을 반환한다. 연속 페이지 탐색이 구현된 것으로 설명하지 않는다.

추천 입력은 document_id 단독 또는 question/document_ids 조합이다. 질문은 최대 500자, document_ids는 최대 10개이며 ID 형식 검증이 있다.

## 4. 제보·관리자

| 메서드 | 경로 | 목적 | 권한 |
|---|---|---|---|
| GET / POST | /v1/me/error-reports | 본인 제보 목록·등록 | 회원 |
| GET | /v1/me/error-reports/{id} | 본인 제보 상세 | 회원 |
| GET | /v1/admin/session | 관리자 인증 상태 | 별도 관리자 설정 |
| POST | /v1/admin/login | 관리자 비밀번호 인증 | 비밀번호 확인 |
| POST | /v1/admin/logout | 관리자 쿠키 종료 | 별도 인증 없이 호출 가능 |
| GET | /v1/admin/dashboard | 처리 현황 | 관리자 인증 |
| GET | /v1/admin/users | 유효 세션 기반 이용자 목록 | 관리자 인증 |
| GET | /v1/admin/searches | 회원 검색 기록 목록 | 관리자 인증 |
| GET | /v1/admin/searches/{id} | 회원 검색 기록 상세 | 관리자 인증 |
| GET | /v1/admin/error-reports | 제보 목록 | 관리자 인증 |
| GET / PATCH | /v1/admin/error-reports/{id} | 제보 상세·처리 변경 | 관리자 인증 |

관리자는 별도 서명 쿠키를 사용하며 유효기간은 8시간이다. 회원의 `role=admin` 여부만으로 접근을 판정하지 않는다.

### 오류 제보의 입력과 저장

| 구분 | 현재 동작 |
|---|---|
| 기본 웹 화면 | 오류 유형 한 가지와 10~2,000자의 설명을 전송한다. 선택한 답변 문구는 설명에 덧붙인다 |
| 서버 요청 | `category` 한 가지 또는 `categories` 배열을 받는다. `selected_quotes`에는 답변에서 선택한 문구를 최대 5개까지 전달할 수 있다 |
| 서버 저장 | `error_reports`에 제보 본문·상태를 저장하고, `error_report_types`에 유형별 한 행, `error_report_quotes`에 선택 문구별 한 행을 저장한다 |
| 서버 응답 | 전체 유형을 `categories` 배열로 제공한다. 이전 화면과의 호환을 위해 첫 유형을 `category`에도 담는다 |

유형 코드는 `incorrect_fact`(사실이 틀림), `citation_mismatch`(출처가 맞지 않음), `incomplete_answer`(설명이 부족함), `inappropriate_content`(부적절한 내용), `other`(기타)다. **기타 유형을 선택했거나 선택 문구가 없으면 설명을 10~2,000자로 작성해야 한다.** 선택 문구가 있고 기타 유형이 아니라면 설명을 비워 둘 수 있다. 현재 서버는 제보 이미지 첨부를 받지 않는다.

```json
{
  "search_record_id": "00000000-0000-4000-8000-000000000000",
  "categories": ["incorrect_fact", "citation_mismatch"],
  "content": "답변의 연도와 인용 출처를 확인해 주세요.",
  "selected_quotes": [{"text": "답변에 실제 포함된 문구"}]
}
```

위 JSON은 요청 구조 예시다. 실제 등록에는 본인 검색 기록 ID와 해당 답변에 존재하는 문구를 사용한다. 선택 문구의 위치(`start_offset`, `end_offset`)는 둘 다 보내거나 둘 다 생략해야 한다.

## 5. 오류 응답

애플리케이션 오류는 주로 `{"error":{"code":"…","message":"…"}}` 형태이다. CSRF·허용하지 않는 메서드 등 프레임워크 오류가 항상 같은 JSON이라고 가정하지 않는다.

| 상태 코드 | 확인된 대표 경우 |
|---|---|
| 400 | JSON 형식이나 요청 구조가 잘못됨 |
| 401 | 회원 또는 관리자 인증 필요 |
| 404 | 개인 결과 없음·권한 없음, 공유 결과 없음 |
| 409 | 이메일 중복 |
| 422 | 질문·설명 수준 등 입력 조건 위반 |
| 502 | RAG 연결·처리 실패 |
| 503 | 관리자 비밀번호 미설정, 연관 탐색 서비스 사용 불가 |

사용자 검색 기록의 `next_cursor`는 현재 `null`이며 관리자 이용자·검색 목록만 `limit`와 `offset`을 사용한다. 페이지를 계속 넘길 수 있다고 가정하지 않는다.

구현 자료: [상세 명세](../api/API_SPEC.md), [라우팅](../../backend/api/urls.py), [요청 처리](../../backend/api/views.py), [공유](../../backend/api/search_links.py), [연관 탐색](../../backend/api/network_views.py).
