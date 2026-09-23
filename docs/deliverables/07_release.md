# 3차·4차 앱 실행 및 제출 안내

## 1. 제출 구성

| 제출 대상 | 설명 | 확정할 항목 |
|---|---|---|
| 3차 앱 | 기존 Streamlit LLM 앱과 당시 실행·평가 근거 | 3차 제출 커밋·필수 데이터·재현 |
| 4차 앱 | React·Django와 재사용 RAG가 연결된 웹 앱 | 최종 커밋·DB·모델·실행 설정 |
| 보고서 | 요구사항·화면·구성도·ERD·API·시험 | 동일 기준 커밋으로 내용 통일 |
| 실행 증거 | 실제 동작 캡처·녹화·검사 결과 | 모의 응답과 실제 동작 구분 |

3차 앱은 [기존 저장소](https://github.com/SpicyAutumn/SKN33-3rd-1Team)와 당시 제출 버전을 기준으로 보존한다. 현재 4차 루트의 run.py 경로가 남아 있다는 것만으로 원래 3차 제출물과 같다고 판단하지 않는다.

## 2. 4차 로컬 실행 준비

| 준비물 | 확인 내용 |
|---|---|
| Git·Docker | 코드 복제, 컨테이너 실행 가능 |
| 비공개 환경 설정 | Django·MySQL·검색·Ollama 연결 정보 |
| 검색 자료 | data/processed/aks_bm25_v1.sqlite3 |
| 사진 자료 | data/processed/aks_article_medias.jsonl |
| 원본 목록 | data/manifest.csv 및 실제 코드 참조 자료 |
| 외부 서비스 | DB·Pinecone·임베딩·Ollama 접속 준비 |

설정 항목 이름은 `MYSQL_*`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` 등을 확인한다. 실제 값은 저장소·보고서·캡처에 넣지 않는다.

기준 Compose는 두 데이터 파일을 읽기 전용으로 연결한다. 실행 전에 경로가 디렉터리가 아닌 정상 파일인지 확인한다. 파일 배치가 변경되면 Compose와 문서를 함께 수정한다.

```powershell
git clone https://github.com/SpicyAutumn/SKN33-4th-1Team.git
cd SKN33-4th-1Team
# 담당자 안내에 따라 비공개 설정·데이터·DB 구조를 준비한 뒤
docker compose up --build -d
docker compose ps
```

운영 서비스: [https://skn33heritage.site/](https://skn33heritage.site/)

로컬 웹: `http://localhost:8081/`

로컬 상태 확인: `http://localhost:8081/api/health`

운영 서비스 이용과 개발용 로컬 실행을 구분한다.

DB migration은 테이블을 생성·변경하므로 대상 DB와 백업을 확인한 담당자만 진행한다. Docker에서 127.0.0.1은 컨테이너 자신이므로 외부 DB·모델 서버 주소와 혼동하지 않는다.

## 3. 실제 실행 확인 순서

1. 컨테이너와 상태 API 확인.
2. 테스트 계정 로그인.
3. 실제 질문의 검색·생성·사진·출처 확인.
4. 개인 주소·검색 기록 재열기와 접근 제한 확인.
5. 공유·제보·관리자 처리 확인.
6. 결과를 테스트 보고서에 기록.

운영 HTTPS 구성은 로컬 Compose와 구분한다. [Docker 안내](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/docs/DOCKER_RUNBOOK.md), [HTTPS 설정](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/docs/MAIN_HTTPS.md), [공용 테스트](https://github.com/SpicyAutumn/SKN33-4th-1Team/blob/7811a717e39a853a01c2bb860b6296b38ba48ea0/docs/COMMON_INTEGRATION_TEST.md)를 참조하되 문서의 과거 진행 상태와 실제 배포 상태를 대조한다.

## 4. 최종 저장소 선별 기준

| 구분 | 처리 기준 |
|---|---|
| 실행 코드·설정 예시 | 실제 앱·빌드·자동 검사에 필요한 파일 유지 |
| 데이터 준비 안내 | 원본 목록·스키마·수집/전처리 절차·접근 방법 보존 |
| 실험 근거 | 최종 선택을 설명하는 비교 결과·한계·최소 재현 코드 선별 |
| 과거 기획 | 필요 시 기록 폴더로 구분; 현재 기능으로 오해하지 않게 안내 |
| 임시 출력·캐시 | 참조가 없고 재생성 가능함을 확인한 뒤 별도 정리 |
| 비공개 자료 | 인증 정보·DB 복제본·개인정보·내부 작업 메모 공유 제외 |

폴더 이름만으로 보존 여부를 결정하지 않는다. `app/`의 일부 파일은 실제 RAG 실행에 사용되며, 실험 폴더의 테스트가 자동 검사에 연결된 경우도 있다.

파일을 정리할 때는 실행 코드·빌드·자동 검사·문서의 참조를 함께 확인한다.

## 5. 제출 전 확인

- [ ] 제출 코드와 문서의 기능·경로 일치
- [ ] 3차·4차 실행 진입점과 필요한 자료 구분
- [ ] ERD·모델·migration·API 일치
- [ ] 최종 화면과 테스트 증거 반영
- [ ] 새 환경에서 안내대로 실행 재현
- [ ] 비밀 값·개인정보·DB 덤프 제외
- [ ] 최종 제출 커밋 또는 태그, 압축파일 목록·체크섬 기록
- [ ] 팀 확인 후 제출본으로 승인

체크섬은 파일이 전달 과정에서 바뀌지 않았는지 확인하는 값이다. 제출 파일을 만든 뒤 실제 계산값을 기록하며 미리 임의 값을 넣지 않는다.
