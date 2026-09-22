# 메인 DB 복제본으로 테스트하기

## 목적과 범위

테스트 서버는 `http://3.36.47.113`, 전용 Compose 프로젝트는 `heritage-integration`이다.
메인 DB의 스키마·ID·FK·마이그레이션 이력을 테스트 MySQL `integration`으로 복원한다.
회원 이메일·이름·비밀번호, 질문·답변·신고 내용은 테스트 값으로 치환한다.
세션·관리자 로그 행은 제외하고 공유 토큰은 제거한다. 복제 회원은 로그인할 수 없으므로
기능 테스트 계정은 별도로 회원가입한다. 원본 운영 `.env`를 EC2나 GitHub에 올리지 않는다.

이 변경은 DB 보존·복제 인프라만 다룬다. DB 정리 브랜치의 컬럼·테이블 삭제는 포함하지 않는다.
원본 생성 AI 응답의 문구 품질 검증용이 아니라 DB 변경·관계·화면 동작 검증용이다.

## 1. 로컬에서 읽기 전용 내보내기

mysqlclient가 설치된 Python으로 실행한다. source-env는 로컬의 원본 접속 설정 파일이다.

```text
python scripts/integration/clone_database.py export --source-env /private/main.env --output /private/seed/snapshot.json
```

- REPEATABLE READ + READ ONLY + consistent snapshot으로 읽는다. InnoDB만 허용한다.
- 내보내는 동안 DDL 변경이 감지되면 중단한다. 운영 마이그레이션과 동시에 실행하지 않는다.
- 검토하지 않은 테이블·컬럼이 생기면 개인정보 처리 규칙을 먼저 보완하도록 실패한다.
- 원본 데이터 덤프를 파일로 저장하지 않고 치환된 JSON만 기록한다.
- 토큰 원문·접속 비밀번호는 결과나 로그에 출력하지 않는다.
- 스냅샷은 행을 메모리에 모으므로 현재 프로젝트 규모용이다. 대규모 DB에는 스트리밍 구현이 필요하다.

## 2. 테스트 서버에서 최초 복원 준비

서버의 `.test-server` 표식과 대상 EC2를 확인한다. 검토된 새 배포 컨트롤러를 먼저 설치한다.
`pull_request_target` 워크플로는 main의 컨트롤러를 사용한다. 이 브랜치 PR에 preview 라벨을
붙이는 것만으로 기존 main 컨트롤러가 바뀌지는 않는다. **인프라 변경을 main에 먼저 반영한 후**
DB 정리 PR의 preview 배포를 진행한다. 인프라 변경은 운영 DB 스키마를 수정하지 않는다.

신뢰하는 운영자가 치환된 snapshot.json만 서버에 전송하고 다음 위치에 둔다.

```text
/srv/heritage-test/seed/snapshot.json
```

폴더는 ubuntu 소유 0700, 파일은 0600으로 제한한다. 공개 웹 폴더·저장소·Actions artifact에 올리지 않는다.
복원은 DB가 완전히 비어 있을 때만 수행하며, 기존 테이블이 있으면 수동 restore는 거절한다.
배포 bootstrap은 기존 DB가 있으면 seed를 재수입하지 않고 migrate만 수행한다.

기존 테스트 볼륨이 있다면 자동으로 지우지 않는다. 먼저 기존 DB를 백업하고,
새 빈 테스트 볼륨으로 교체할지 명시적으로 결정해야 한다. 운영 DB·볼륨을 이 작업에 사용하지 않는다.
원본 스냅샷이 필요 없는 새 환경은 seed 없이 기존 초기화 경로를 쓸 수 있다.

새 컨트롤러는 마지막 배포의 mysql.env가 있으면 기존 비밀번호를 한 번 인계한다.
볼륨은 있지만 마지막 배포 정보와 안정된 mysql.env가 모두 없다면 시작을 거절한다.
이 경우 기존 비밀번호를 복구해야 하며, 새 비밀번호로 덮어쓰지 않는다.

## 3. 최초 배포와 이후 배포

1. 컨테이너 이미지 빌드에 성공한 뒤 이전 앱을 중지한다. 볼륨은 삭제하지 않는다.
2. DB를 시작하고 접속 준비를 확인한다.
3. 현재 테스트 DB를 `releases/<release>/before-migrate.sql`에 백업한다.
4. 빈 DB에 seed가 있으면 복원하고 FK 고아 행을 확인한다. 이후 마이그레이션을 실행한다.
5. 백엔드·프론트엔드와 HTTP 검증이 모두 성공하면 active.json을 갱신한다.

DB 삭제 옵션 `down --volumes`는 사용하지 않는다. preview 라벨을 모두 제거해 최신 main으로 전환되어도
DB·자격 증명·최종 배포 정보는 남고 사이트는 계속 실행된다. 다음 배포에서 같은 데이터를 사용한다.
seed는 자동 재수입되지 않는다. 다시 원본 시점으로 시작하려면 별도 백업·복원 절차가 필요하다.

복원 도구를 독립 실행하려면 테스트 컨테이너 내에서 다음 명령을 사용한다.
target-env에는 INTEGRATION_DATABASE=1, MYSQL_DATABASE=integration과 테스트 접속 정보가 필요하다.
허용 호스트는 db 또는 로컬 loopback뿐이다. 터널이 원본 DB를 가리키지 않는지 운영자가 확인한다.

```text
python clone_database.py restore --snapshot /private/snapshot.json --target-env /private/test.env
```

## 4. 실패·복구

MySQL DDL은 전체를 트랜잭션으로 되돌릴 수 없다. 마이그레이션·앱 검증에 실패하면
`database-review-required.json` 표식을 남기고 앱을 중지한다. 다음 자동 배포도 차단한다.
이전 버전 코드를 변경된 DB에 자동 실행하거나, 테스트 DB를 지워서 성공처럼 처리하지 않는다.
복원 도중 실패해도 생성된 테이블은 남을 수 있다. 비어 있지 않은 대상에 재수입을 강행하지 않는다.

운영자는 표식에 기록된 실패 배포와 before-migrate.sql을 확인하고, 다음 중 하나를 택한다.

- 변경된 스키마에 맞는 수정 코드를 준비하고 적용 상태를 확인한 뒤 배포를 재개한다.
- 테스트 앱을 중지한 상태에서 별도 빈 테스트 DB/볼륨에 변경 전 백업을 복원하고 이전 코드로 검증한다.

복구와 자격 증명 일치를 확인한 후에만 표식을 제거한다. 표식만 지우는 것은 복구가 아니다.
백업과 이전 소스는 자동 삭제하지 않는다. 테스트 기간과 디스크 공간에 맞춰 수동 보관 정책을 적용한다.
SQL 백업에는 테스트 입력이 포함되므로 seed와 동일한 권한으로 관리한다.

## 검증과 메인 반영

- 단위 테스트: `python -m pytest -q tests/test_integration_server.py tests/test_integration_clone.py`
- 로컬 실제 MySQL: 메인 15개 테이블의 치환본 복원, 행 수 일치, 로그인 불가 비밀번호·공유 토큰 제거 확인.
- 복제본에서 main 코드의 migrate, 새 회원가입·인증·검색·비공개 접근 차단·공개 공유·신고 smoke 확인.
- 이후 DB 정리 PR로 기존 구조에서 새 구조로 변경되는 절차를 별도 검증한다.
- 메인 반영 시 복제 DB를 역복사하지 않는다. 검증한 코드와 마이그레이션만 배포한다.

2026-09-22에 테스트 EC2에 최신 main(`0717e2e`)과 비식별 복제본을 배포했고,
DB·백엔드·프런트엔드 health check 및 HTTP 응답을 확인했다.
기존 main 컨트롤러의 볼륨 삭제를 피하기 위해 현재 실행본은
`/srv/heritage-test/clone-lab`, Compose 프로젝트 `heritage-db-clone`,
볼륨 `heritage-db-clone_db`를 사용한다. 이 실행본은 preview PR 없이 유지된다.

자동 배포 통합은 별도 전환이 필요하다. 현재 main의 기존 워크플로는 여전히
`heritage-integration`을 대상으로 하므로 새 preview 배포를 실행하면 80번 포트가 충돌할 수 있다.
이 인프라 변경을 main에 반영하고, 테스트 DB를 백업한 뒤 실행본의 경로·프로젝트·볼륨·
자격 증명을 자동 배포 대상과 일치시키는 전환을 먼저 수행한다.
전환 전에 기존 워크플로로 새 preview를 배포하지 않는다. 운영 DB에는 변경하지 않았다.

preview PR이 0개여도 최신 main을 빌드·배포한다. 다만 PR의 DB 변경이 main 코드와 호환되지 않으면 자동 역마이그레이션하지 않는다. 실제 기능 확인 후 복구/다음 코드 배포를 결정한다.
