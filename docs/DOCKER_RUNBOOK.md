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

검색 결과에 공공누리 이미지를 표시하려면 팀 드라이브에서 받은
`aks_article_medias.jsonl`을 `data/processed/aks_article_medias.jsonl`에 둔다.
Docker Compose가 이 파일을 backend 컨테이너의
`/data/aks_article_medias.jsonl`에 읽기 전용으로 연결한다. 파일이 없으면 텍스트
검색은 계속 동작하지만 `/api/health`의 `media_catalog`이 `missing`으로 표시되고
검색 응답의 `media`는 빈 배열이 된다.

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

## 실제 RAG 검색 확인

현재 React는 `POST /api/v1/searches`를 호출하고 Django가 기존 `RagService`를
실행한다. `.env`에 OpenAI·Pinecone·Ollama 설정이 있어야 실제 답변이 반환된다.

`aks_bm25_v1.sqlite3`는 약 692MB이므로 Docker 이미지나 Git에 넣지 않는다.
정상 파일을 `data/processed/aks_bm25_v1.sqlite3`에 두면 Hybrid 검색을 사용한다.
파일이 없으면 Pinecone Dense 검색으로 자동 전환되므로 실제 검색 자체는 확인할 수
있다. 단, 같은 이름의 빈 폴더가 생겼다면 실제 SQLite 파일로 교체하기 전에 그 빈
폴더를 제거해야 한다.
