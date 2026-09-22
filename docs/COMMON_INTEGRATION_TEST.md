# 공용 통합 테스트 사이트

`preview` 라벨이 붙은 같은 저장소의 열려 있는 PR을 PR 번호순으로 최신 `main` 위에 합쳐, 전용 EC2의 한 개 사이트에 배포한다. 이 사이트는 병합 전 기능 조합을 확인하는 용도이며 운영 사이트가 아니다.

## 팀 사용법

1. 개발 PR을 열고 기본 단위 테스트를 통과시킨다.
2. 다른 PR과 함께 확인할 준비가 되면 PR에 `preview` 라벨을 붙인다. 초안 PR도 라벨이 있으면 포함된다.
3. GitHub Actions의 **Common integration test**가 성공하면 실행 요약에서 공용 테스트 URL과 포함된 PR 목록을 확인한다.
4. 문제가 있으면 `preview` 라벨을 제거한다. 해당 PR은 다음 통합 배포에서 제외된다.

같은 라벨의 PR끼리 충돌하면 빌드 전 실패하므로 기존 사이트와 DB는 유지된다.
마이그레이션 시작 이후 실패하면 DB와 변경 전 백업을 보존하고 앱을 중지한다.
변경된 DB에 구버전 코드를 자동으로 시작하지 않는다. 복구 절차는 아래 문서를 참고한다.

## 데이터와 DB

- 테스트 EC2와 테스트 MySQL 컨테이너는 운영 EC2·공유 MySQL과 완전히 분리된다.
- 통합 구성이 바뀌거나 preview PR이 없어 앱을 중지해도 MySQL 볼륨은 유지된다.
- DB 자격 증명은 `/srv/heritage-test/mysql.env`에 보관하고 배포마다 재사용한다.
- 마이그레이션 전에 해당 배포 디렉터리에 `before-migrate.sql` 백업을 남긴다.
- 메인 DB 복제는 [복제·복구 절차](TEST_DATABASE_CLONE.md)를 따른다. 운영 인증 정보는 테스트 서버로 전달하지 않는다.
- `/srv/heritage-test/test-api.env`의 AI/RAG 변수만 테스트 컨테이너에 전달한다. 운영 `.env`, `MYSQL_*`, `DJANGO_SECRET_KEY`는 전달하지 않는다.
- 라벨을 붙일 권한은 팀 저장소에서 신뢰하는 구성원에게만 준다. 라벨이 붙은 PR 코드는 테스트 EC2에서 빌드·실행된다.

## AWS/GitHub 초기 설정

GitHub Actions 변수:

| 이름 | 값 |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `TEST_INSTANCE_ID` | 테스트 EC2 인스턴스 ID |
| `AWS_TEST_DEPLOY_ROLE_ARN` | 테스트 전용 GitHub OIDC 역할 ARN |
| `TEST_SITE_URL` | 테스트 사이트의 HTTP 주소 |
| `INTEGRATION_TEST_ENABLED` | `true` |

테스트 전용 OIDC 역할은 SSM `SendCommand`를 테스트 EC2 하나에만 허용해야 한다. 운영 배포 역할과 인스턴스 ID는 재사용하지 않는다.

테스트 서버에는 다음 파일이 있어야 한다.

```text
/srv/heritage-test/.test-server
/srv/heritage-test/server.json
/srv/heritage-test/test-api.env
/srv/heritage-test/data/aks_bm25_v1.sqlite3
/srv/heritage-test/data/aks_article_medias.jsonl
```

현재 테스트 URL은 `http://3.36.47.113`이다. 인스턴스를 중지 후 시작하면 공인 IP가 바뀔 수 있으므로, 장기간 운영할 때는 Elastic IP를 붙인다.
