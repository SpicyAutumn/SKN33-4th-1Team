# 오늘 시연할 MVP

## 포함

- React 기반 질문 화면
- Django와 `django_project4` MySQL을 사용하는 회원가입·로그인·로그아웃
- `POST /api/chat` 응답 계약과 답변·출처 카드 표시

## 시연 모드 제한

현재 `.env`에는 OpenAI, Pinecone, Ollama 연결값이 없어 실제 RAG를 호출하지 않는다. `/api/chat`은 이 사실을 명시한 시연 응답을 반환한다. 키와 서비스 주소가 준비되면 같은 endpoint에서 기존 `RagService`를 호출하도록 교체한다.

## 제외

- 최근 검색·즐겨찾기·오류 제보 DB 테이블
- 실제 RAG 호출
- Docker·외부 배포
- Figma의 네 번째 설명 수준(기존 RAG는 3단계)

## 배포 전 보완

- 회원가입·로그인 endpoint에 임시로 적용한 CSRF 예외를 제거하고, React 요청에 CSRF 토큰을 붙인다.
- `DEBUG`, `SECRET_KEY`, 허용 도메인, HTTPS 쿠키 설정을 배포 환경 값으로 바꾼다.
- 제공된 `accounts_user` 테이블은 Django가 자동 변경하지 않도록 `managed=False`로 연결했다. 테이블 구조를 바꾸는 작업은 팀 합의 후 별도 마이그레이션으로 진행한다.
