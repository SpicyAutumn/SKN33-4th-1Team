# 공용 통합 테스트 사이트

`preview` 라벨이 붙은 같은 저장소의 열려 있는 PR을 PR 번호순으로 최신 `main` 위에 합쳐, 전용 EC2의 한 개 사이트에 배포한다. 이 사이트는 병합 전 기능 조합을 확인하는 용도이며 운영 사이트가 아니다.

## 팀 사용법

1. 개발 PR을 열고 기본 단위 테스트를 통과시킨다.
2. 다른 PR과 함께 확인할 준비가 되면 PR에 `preview` 라벨을 붙인다. 초안 PR도 라벨이 있으면 포함된다.
3. GitHub Actions의 **Common integration test**가 성공하면 해당 PR의 봇 댓글에서 공용 테스트 URL과 포함된 PR 목록을 확인한다.
4. 문제가 있으면 `preview` 라벨을 제거한다. 해당 PR은 다음 통합 배포에서 제외된다.

같은 라벨의 PR끼리 충돌하면 새 배포는 실패하고, 이전에 정상 배포된 테스트 사이트는 복구된다. 충돌을 해결하거나 라벨을 제거한 뒤 다시 실행한다.

## 데이터와 DB

- 테스트 EC2와 테스트 MySQL 컨테이너는 운영 EC2·공유 MySQL과 완전히 분리된다.
- 통합 구성이 바뀔 때 테스트 MySQL 볼륨을 다시 만들므로 테스트 계정, 검색 기록, 오류 신고는 매번 초기화된다.
- `/srv/heritage-test/test-api.env`의 AI/RAG 변수만 테스트 컨테이너에 전달한다. 운영 `.env`, `MYSQL_*`, `DJANGO_SECRET_KEY`는 전달하지 않는다.
- 라벨을 붙일 권한은 팀 저장소에서 신뢰하는 구성원에게만 준다. 라벨이 붙은 PR 코드는 테스트 EC2에서 빌드·실행된다.

## AWS/GitHub 초기 설정

GitHub Actions 변수:

| 이름 | 값 |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `TEST_INSTANCE_ID` | 테스트 EC2 인스턴스 ID |
| `AWS_TEST_DEPLOY_ROLE_ARN` | 테스트 전용 GitHub OIDC 역할 ARN |
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
