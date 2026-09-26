# main 자동 배포 설정

이 설정은 기존 앱 파일을 바꾸지 않고 GitHub Actions → AWS OIDC → Systems Manager Run Command → EC2 Docker Compose로 배포합니다. SSH 인바운드를 GitHub에 개방하거나 PEM 키, AWS 장기 액세스 키, `.env`를 GitHub에 등록할 필요가 없습니다.

## 병합 전 실배포 검증 결과

2026-09-20에 작업 브랜치의 배포 스크립트로 테스트를 통과한 main `7ef670e7fcf7e41f7a00b2ddb5b3e36efe66c28e`를 실제 EC2에 재배포했습니다.

- [GitHub Actions 실행 결과: 성공](https://github.com/SpicyAutumn/SKN33-4th-1Team/actions/runs/35516185247)
- GitHub OIDC 인증, SSM 명령 전송, Docker 빌드, MySQL SELECT 1, 컨테이너 교체, 웹 및 API health 응답 검사 통과
- SSM Command ID: `d5c4a3a7-ba0d-46ab-98f9-241ece6f87dc`
- 실배포에 사용한 배포 스크립트는 그대로 유지하고, 검증 후 임시 브랜치 push 트리거를 제거했습니다.
- IAM 신뢰 정책에서도 검증 브랜치 허용 항목을 제거하고 아래 main 전용 정책을 유지하세요.

이는 실제 배포 경로 검증 결과입니다. main 병합에 의해 자동으로 이어지는 `workflow_run` 트리거는 병합 후 첫 실행에서 별도로 확인해야 합니다. 실제 장애를 강제로 발생시키는 운영 롤백 실험은 하지 않았고 실패 처리에는 모의 검증을 사용했습니다.

## 배포 조건과 범위

- `Python tests`의 main push 성공으로 배포 준비를 시작하고, **같은 커밋의 Python tests·Frontend checks·Heritage network checks가 모두 성공**해야 AWS 인증과 배포를 진행합니다.
- 대기 전용 `checks` 작업은 최대 15분 동안 나머지 검사를 확인합니다. 누락·실행 중인 검사는 성공으로 간주하지 않으며 시간 초과 시 배포를 차단합니다. 대기 작업에는 AWS 인증 권한이 없습니다.
- 성공 기록만 검색하지 않고 각 워크플로의 최신 실행/재실행 상태를 확인합니다. 이전 성공 뒤 최신 실행이 실패·취소·건너뜀 상태면 배포하지 않습니다.
- PR 테스트만으로는 배포하지 않습니다. PR은 기존 CONTRIBUTING.md에 따라 팀원 승인을 받고 병합합니다.
- 수동 실행도 main에서만 가능하며 동일한 3개 검사의 main push 성공을 확인합니다. PR 검사의 성공이나 다른 커밋의 결과로 대신하지 않습니다.
- 검사가 모두 끝난 뒤와 실제 배포 작업 시작 시 최신 main과 검사 상태를 재확인합니다. 프런트 검사는 문서 변경만 있는 경우에도 실행해 커밋별 배포 조건이 누락되지 않게 합니다.
- 오래된 테스트 결과가 뒤늦게 도착하면 최신 main과 다른 커밋의 배포를 거부합니다.
- 서버 경로는 `/home/ubuntu/SKN33-4th-1Team`, 실행 사용자는 `ubuntu`입니다.
- `.env`와 `data/processed`는 EC2의 기존 파일을 사용합니다. 복사·삭제·출력하지 않습니다.
- EC2에서 이미 실행 중인 backend/frontend 컨테이너가 있어야 합니다.
- 서버에서 코드를 직접 수정하지 마세요. 배포 후 checkout은 검증한 SHA의 detached HEAD 상태입니다.
- 빌드 및 DB 연결 확인 후 컨테이너를 교체합니다. 단일 서버라 짧은 중단이 있으며 무중단 배포가 아닙니다.
- 전환 실패 시 직전 코드/이미지로 복구를 시도합니다. DB 마이그레이션은 실행하지 않으며, DB 데이터와 외부 API 동작까지 되돌리는 기능은 아닙니다.
- DB 구조 변경은 별도 검토와 마이그레이션 절차가 필요합니다. SELECT 1은 연결 검사일 뿐 모든 테이블 존재나 기능을 검증하지 않습니다.

## 1. EC2를 Systems Manager에 연결

AWS IAM에서 EC2용 역할을 만들고 `AmazonSSMManagedInstanceCore` 관리형 정책을 연결합니다. EC2 콘솔 → 인스턴스 → 작업 → 보안 → IAM 역할 수정에서 연결하세요. 기존 역할이 있으면 이를 대체하지 말고 필요한 정책을 추가합니다.

Ubuntu 서버에서 SSM Agent 설치/실행 여부를 확인합니다.

```bash
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service --no-pager
```

Agent가 없다면 AWS 공식 Ubuntu 설치 안내에 따라 설치합니다. AWS Systems Manager 콘솔에서 인스턴스가 관리 노드로 표시되고 온라인인지 확인해야 합니다. SSM 서비스로 나가는 HTTPS(443) 연결이 필요합니다. 기존 SSH의 '내 IP' 규칙은 유지합니다.

## 2. GitHub OIDC 공급자 및 배포 역할

IAM → 자격 증명 공급자에 다음 OIDC 공급자를 등록합니다(이미 있으면 재사용).

- URL: `https://token.actions.githubusercontent.com`
- 대상(Audience): `sts.amazonaws.com`

아래 신뢰 정책으로 별도의 `GitHubMainDeployRole` 역할을 만듭니다. `ACCOUNT_ID`를 실제 AWS 계정 ID로 교체하세요. **이 저장소의 main만** 역할을 사용할 수 있습니다. 워크플로에 GitHub `environment`를 추가하면 OIDC subject가 달라지므로 정책도 별도로 조정해야 합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:SpicyAutumn@285661806/SKN33-4th-1Team@1359779121:ref:refs/heads/main"
    }}
  }]
}
```

이 역할에 다음 인라인 권한 정책을 연결합니다. `REGION`, `ACCOUNT_ID`, `INSTANCE_ID`를 실제 값으로 교체하세요. 서울 리전은 `ap-northeast-2`입니다. EC2 ID는 `i-`로 시작하며 퍼블릭 IP와 다릅니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ssm:REGION::document/AWS-RunShellScript",
        "arn:aws:ec2:REGION:ACCOUNT_ID:instance/INSTANCE_ID"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "ssm:GetCommandInvocation",
      "Resource": "*"
    }
  ]
}
```

Run Command는 대상 서버에서 관리자 명령을 실행할 수 있으므로 main 병합 권한을 팀에서 관리해야 합니다.

이 저장소는 이름뿐 아니라 소유자 ID와 저장소 ID를 포함하는 GitHub의 immutable OIDC subject 형식을 사용합니다. 실제 검증 실행에서 `sub`를 확인했습니다. 이름만 적은 구형 정책으로는 인증되지 않습니다. 임시 검증 브랜치는 위 값의 마지막 `main`만 `codex/main-auto-deploy`로 바꾼 값을 배열에 추가하고, 검증 후 제거합니다.

## 3. GitHub 저장소 변수 3개

GitHub → Settings → Secrets and variables → Actions → **Variables**에 추가합니다.

| 이름 | 값 |
| --- | --- |
| `AWS_REGION` | `ap-northeast-2` |
| `EC2_INSTANCE_ID` | 새 서버의 `i-...` ID |
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::계정ID:role/GitHubMainDeployRole` |

이 값들은 비밀번호가 아닙니다. `.env`, PEM 파일, DB 비밀번호를 업로드하지 않습니다.

## 4. 검증 및 활성화

1. EC2에서 기존 사이트와 MySQL 연결이 정상인지 확인합니다.
2. 위 AWS 연결과 GitHub 변수를 준비합니다.
3. 설정 PR을 팀원 검토 후 main에 병합합니다. 이때부터 배포가 활성화됩니다.
4. Actions에서 Python tests·Frontend checks·Heritage network checks를 확인하고, Deploy main to EC2의 `checks` → `deploy` 순서가 성공하는지 확인합니다.
5. 실제 사이트의 화면과 로그인/검색 기능을 확인합니다. CI와 health 검사만으로 외부 AI 서비스까지 보장하지 않습니다.
6. 검사 실패·취소 시 해당 검사를 먼저 재실행합니다. 세 검사 모두 성공한 뒤 Actions → Deploy main to EC2 → Run workflow → main으로 배포를 재시도합니다. 프런트·연관 탐색 검사만 재실행해 성공한 경우 배포를 자동으로 다시 시작하지는 않습니다.

현재 워크플로는 AWS 인증을 main으로 제한하므로 기능 브랜치에서 운영 서버에 수동 배포할 수 없습니다. 병합 전 로컬 검사는 구문과 로직 검사이며 실제 OIDC/SSM 연결 검증과 다릅니다.

## 자동 검사의 역할

| 워크플로 | 담당 검사 |
|---|---|
| Python tests | 공통 Python 테스트(연관 탐색 로직 포함), 백엔드 API·검색 공유·DB 구조, 오프라인 실험 |
| Frontend checks | 프런트 전체 테스트(연관 탐색 상태 포함), 제보·사진·로딩·재질문 검사와 제품 빌드 |
| Heritage network checks | 별도 Django 연관 탐색 API 테스트 |

중복 실행하던 공통 Python 검사·프런트 검사·빌드는 각각 담당 워크플로로 모았습니다. 기존 워크플로 이름과 작업 ID는 유지합니다. 공용 통합 테스트는 별도 EC2 구성·배포이며 운영 배포의 필수 검사 목록과 구분합니다. [워크플로 안내](../.github/workflows/README.md)를 참고하세요.

## 운영 시 유의점

- Actions를 중간에 취소해도 이미 전송된 SSM 명령은 서버에서 계속 실행될 수 있습니다. SSM 콘솔에서 해당 Command ID 상태를 먼저 확인하세요. 서버 파일 잠금으로 중복 실행은 거부합니다.
- 빌드/롤백 이미지와 캐시는 디스크를 사용합니다. `sudo docker system df`로 확인하고 프로젝트 종료 후 필요한 데이터 보관 여부를 확인하여 리소스를 정리하세요. 배포 스크립트는 다른 컨테이너에 영향을 줄 수 있는 전역 prune을 실행하지 않습니다.
- 저장소가 비공개로 바뀌면 서버의 읽기 전용 Git 인증을 별도로 설정해야 합니다. 현재 서버의 origin 인증을 사용합니다.
- API 키와 DB 정보가 들어갈 수 있으므로 `.env`, `docker compose config` 전체 결과를 Actions 로그에 출력하지 마세요.

## 공식 참고

- [GitHub workflow_run 이벤트](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
- [커밋별 워크플로 실행 조회](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow)

- [GitHub OIDC와 AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [SSM Run Command](https://docs.aws.amazon.com/systems-manager/latest/userguide/walkthrough-cli.html)
- [Ubuntu SSM Agent 설치](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-ubuntu-64-snap.html)
