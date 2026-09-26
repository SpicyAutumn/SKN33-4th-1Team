# 문서 안내

폴더별 역할과 새 파일을 둘 위치는 [파일을 두는 기준](REPOSITORY_STRUCTURE.md)을 따른다.

| 구분 | 위치 | 내용 |
|---|---|---|
| 4차 제출 자료 | [산출물 목차](deliverables/README.md) | 요구사항·화면·구성도·ERD·API·테스트·실행 안내 |
| API 상세 | [API 명세](api/API_SPEC.md) | 요청·응답과 권한 |
| 운영 | [Docker](DOCKER_RUNBOOK.md), [자동 배포](MAIN_AUTO_DEPLOY.md), [HTTPS](MAIN_HTTPS.md) | 실행·배포 설정 |
| 통합 테스트 | [공용 테스트](COMMON_INTEGRATION_TEST.md), [DB 복제](TEST_DATABASE_CLONE.md) | 테스트 환경 운영 |
| 데이터 | [문서 카드](document-card.md), [전처리 보고서](02_data_preprocessing_report.md) | 출처·준비·검증 |
| 실험 | [모델 비교](experiments/FOURTH_QWEN_BASELINE_RECOMMENDATION.md) | 모델·프롬프트·검색 평가 근거 |
| 과거 기록 | [보관 목차](archive/README.md) | 초기 기획·회의·3차 보고서·옛 인계 |

## 파일을 읽는 순서

| 목적 | 먼저 볼 위치 | 구분할 점 |
|---|---|---|
| 현재 서비스 실행 | 루트 `README.md`, `frontend/`, `backend/`, `app/`, `src/` | 실제 화면은 `frontend/index.html`에서 시작한다 |
| 데이터 준비·검증 | `scripts/`, `data/manifest.csv`, `data/evaluation/`, `outputs/` | 원본·검색 인덱스는 저장소에 포함되지 않는다. `manifest.csv`는 현재 Docker 이미지와 연관 자료 탐색에서 사용한다 |
| 자동 검사 | `tests/`, `frontend/tests/`, `.github/workflows/` | `experiments/semantic_verifier/`의 오프라인 검사도 Python CI에 연결돼 있다 |
| 화면 검토 자료 | [개발용 화면 안내](../frontend/src/review/README.md) | 실제 서비스 진입점은 아니다. 일부는 검사 스크립트와 검증 문서에서 사용하므로 일괄 삭제하지 않는다 |
| 검색 비교 구현 | [검색 실험 안내](../experiments/retrieval/README.md) | 운영 검색 구현과 별도로 보존한다 |
| 과거 데이터 인계 | [보관 도구 안내](../scripts/archive/README.md) | 당시 10,000 EID용이며 현재 제출 패키징 도구가 아니다 |
| 검색 입력 실험 | `notebooks/embedding_input_evaluation.ipynb` | 당시 임베딩 입력 비교 기록이며 운영 요청 처리에는 사용하지 않는다 |
| 제출본·근거·과거 기록 | `docs/deliverables/`, `docs/experiments/`, `docs/archive/` | 제출 내용은 `deliverables/`을 기준으로 읽고, 실험 조건과 이전 기록은 구분한다 |

개인 초안은 저장소 루트의 `_local/`에, 재생성 가능한 로컬 출력물은 `output/`에 보관합니다. 두 경로는 Git과 Docker 빌드 대상에서 제외합니다. 공개할 최종 문서는 검토 후 해당 문서 폴더에 추가합니다.
