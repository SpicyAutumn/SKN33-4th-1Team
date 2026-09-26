# 자동 검사와 배포

| 파일 | 실행 조건 | 역할 |
|---|---|---|
| `python-tests.yml` | PR, main·지정 개발 브랜치 push | Python·API·공유·DB·실험 검사 |
| `frontend-tests.yml` | 모든 PR·main push | 프런트 테스트·상태 검사·제품 빌드 |
| `heritage-network-check.yml` | PR·main push | 별도 연관 탐색 API 검사 |
| `deploy-main.yml` | main Python 성공 또는 main 수동 실행 | 같은 최신 main 커밋의 3개 검사 성공 후 운영 배포 |
| `integration-test.yml` | 활성화 설정과 main/preview PR 조건 | 별도 공용 테스트 환경 조합·배포 |

운영 배포의 `checks` 작업은 최대 15분 기다리고, 실패·취소·누락·오래된 커밋을 통과시키지 않습니다. `deploy` 작업은 그 작업에 의존하고 AWS 인증 전에 다시 확인합니다. 프런트·연관 API 검사 재시도만으로 배포가 다시 시작되지는 않으므로 모두 성공한 뒤 운영 배포를 수동 실행합니다.

연관 탐색의 공통 Python 로직은 Python tests, 화면 상태는 Frontend checks에서 검사합니다. 별도 network 작업은 Django API만 검사해 반복 설치·빌드를 줄입니다. 기존 체크 이름은 유지합니다.

검사 워크플로 이름·실행 조건을 변경할 때는 `scripts/deploy/check_required_runs.py`의 필수 목록과 저장소 required checks 설정도 확인합니다. 운영·공용 테스트 배포를 일반 검사처럼 실행하지 않습니다.

자세한 설정과 재시도: [운영 배포 안내](../../docs/MAIN_AUTO_DEPLOY.md), [공용 테스트 안내](../../docs/COMMON_INTEGRATION_TEST.md).
