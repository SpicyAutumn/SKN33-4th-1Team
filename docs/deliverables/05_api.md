# API 명세서

## 1. 공통 규칙

API는 화면과 서버가 요청·응답을 주고받는 규칙이다. 아래 경로는 모두 `/api`로 시작하며 끝에 슬래시를 붙이지 않는다. `{id}`와 `{token}`은 UUID 형식의 식별자이다.

- 읽기는 주로 GET, 생성·처리는 POST, 일부 변경은 PATCH, 탈퇴는 DELETE를 사용한다.
- 회원 인증은 쿠키 기반이다. 변경 요청에는 CSRF 방어 설정을 따른다. CSRF는 다른 사이트가 사용자를 대신해 변경 요청을 보내는 것을 막기 위한 확인이다.
- 개인 결과 접근과 공개 공유 링크 접근은 별개이다.
- 아래 표는 URL·메서드·주요 입력·권한을 다룬다. 경로별 전체 응답 필드와 자료형, 실제 요청·응답 예시는 추가 검증 대상이다.

## 2. 상태·인증·회원

| 메서드 | 경로 | 목적·주요 입력 | 권한 |
|---|---|---|---|
| GET | /health | 서비스 상태 확인 | 공개 |
| GET | /v1/auth/csrf | CSRF 토큰 준비 | 공개 |
| POST | /v1/auth/signup | name, email, password | 공개 |
| POST | /v1/auth/login | email, password | 공개 |
| POST | /v1/auth/logout | 현재 로그인 종료 | 현재 세션 |
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
| POST | /v1/admin/logout | 관리자 쿠키 종료 | 관리자 세션 |
| GET | /v1/admin/dashboard | 처리 현황 | 관리자 인증 |
| GET | /v1/admin/users | 유효 세션 기반 이용자 목록 | 관리자 인증 |
| GET | /v1/admin/searches | 회원 검색 기록 목록 | 관리자 인증 |
| GET | /v1/admin/searches/{id} | 회원 검색 기록 상세 | 관리자 인증 |
| GET | /v1/admin/error-reports | 제보 목록 | 관리자 인증 |
| GET / PATCH | /v1/admin/error-reports/{id} | 제보 상세·처리 변경 | 관리자 인증 |

관리자는 별도 서명 쿠키를 사용하며 유효기간은 8시간이다. 회원의 `role=admin` 여부만으로 접근을 판정하지 않는다. 이 방식의 적정성과 최종 운영 정책은 별도 검토 대상이다.

## 5. 오류 응답

애플리케이션 오류는 주로 `{"error":{"code":"…","message":"…"}}` 형태이다. CSRF·허용하지 않는 메서드 등 프레임워크 오류가 항상 같은 JSON이라고 가정하지 않는다.

| 상태 코드 | 확인된 대표 경우 |
|---|---|
| 401 | 회원 또는 관리자 인증 필요 |
| 404 | 개인 결과 없음·권한 없음, 공유 결과 없음 |
| 409 | 이메일 중복 |
| 422 | 질문·설명 수준 등 입력 조건 위반 |
| 502 | RAG 연결·처리 실패 |
| 503 | 관리자 비밀번호 미설정, 연관 탐색 서비스 사용 불가 |

경로별 전체 요청·응답 필드, 인증·CSRF 예시와 실제 테스트 응답은 추가 확인이 필요하다.

DB 구조 변경으로 필드가 바뀌면 화면과 시험 항목도 함께 수정한다.

근거: [라우팅](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/backend/api/urls.py), [요청 처리](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/backend/api/views.py), [공유](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/backend/api/search_links.py), [추천](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/backend/api/network_views.py).
