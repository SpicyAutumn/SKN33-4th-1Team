# 문서 안내

| 구분 | 위치 | 내용 |
|---|---|---|
| 4차 제출 자료 | [산출물 목차](deliverables/README.md) | 요구사항·화면·구성도·ERD·API·테스트·실행 안내 |
| API 상세 | [API 명세](api/API_SPEC.md) | 요청·응답과 권한 |
| 운영 | [Docker](DOCKER_RUNBOOK.md), [자동 배포](MAIN_AUTO_DEPLOY.md), [HTTPS](MAIN_HTTPS.md) | 실행·배포 설정 |
| 통합 테스트 | [공용 테스트](COMMON_INTEGRATION_TEST.md), [DB 복제](TEST_DATABASE_CLONE.md) | 테스트 환경 운영 |
| 데이터 | [문서 카드](document-card.md), [전처리 보고서](02_data_preprocessing_report.md) | 출처·준비·검증 |
| 실험 | [모델 비교](experiments/FOURTH_QWEN_BASELINE_RECOMMENDATION.md) | 모델·프롬프트·검색 평가 근거 |
| 과거 기록 | [보관 목차](archive/README.md) | 초기 기획·회의·3차 보고서·옛 인계 |

개인 초안은 저장소 루트의 `_local/`에, 재생성 가능한 로컬 출력물은 `output/`에 보관합니다. 두 경로는 Git과 Docker 빌드 대상에서 제외합니다. 공개할 최종 문서는 검토 후 해당 문서 폴더에 추가합니다.
