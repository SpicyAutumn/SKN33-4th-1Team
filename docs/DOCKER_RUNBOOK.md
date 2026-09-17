# Docker 실행 안내

## 구성

- `frontend`: Nginx가 React 빌드 결과를 제공하고 `/api` 요청을 backend로 전달한다.
- `backend`: Gunicorn으로 Django를 실행하고 루트 `.env`의 MySQL 설정으로 원격 `django_project4`에 접속한다.
- MySQL 컨테이너는 만들지 않는다. 강사가 제공한 원격 MySQL을 그대로 사용한다.

## 사전 준비

Windows에서는 Docker Desktop을 설치하고 실행한다. 설치가 끝나면 PowerShell에서 아래 명령이 버전을 표시해야 한다.

```powershell
docker version
```

루트 `.env`에는 최소한 아래 키가 필요하다. 값은 Git에 올리지 않는다.

```env
MYSQL_HOST=
MYSQL_PORT=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
DJANGO_SECRET_KEY=
```

`MYSQL_DATABASE`가 빈 값이면 Django가 `django_project4`를 사용한다.

외부 서버에 배포할 때는 `.env`의 `DJANGO_ALLOWED_HOSTS`에 실제 도메인을 쉼표로 구분해 추가한다.

## 실행

프로젝트 루트에서 실행한다.

```powershell
docker compose up --build -d
docker compose ps
```

브라우저에서 `http://localhost:8081`을 연다. API 상태는 `http://localhost:8081/api/health`에서 확인한다. 로컬 `8080` 포트는 다른 Docker 서비스가 사용 중이므로 이 프로젝트는 `8081`을 사용한다.

로그가 필요하면 다음 명령을 사용한다.

```powershell
docker compose logs -f
```

중지할 때는 다음 명령을 사용한다. 원격 MySQL 데이터는 삭제하지 않는다.

```powershell
docker compose down
```

## 현재 제한과 다음 단계

현재 `/api/chat`은 RAG를 호출하지 않는 시연 모드다. `.env`의 RAG 키가 있어도 Django API에서 `RagService`를 호출하도록 바꾸기 전까지는 실제 검색이 실행되지 않는다.

`aks_bm25_v1.sqlite3`는 약 692MB이므로 Docker 이미지나 Git에 넣지 않는다. RAG 연결 후 배포 서버의 별도 경로에 두고 backend 컨테이너에 읽기 전용 볼륨으로 마운트한다.
