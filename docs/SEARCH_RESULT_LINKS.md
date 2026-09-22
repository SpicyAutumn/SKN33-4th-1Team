# 검색 결과 주소와 공유 (`mk/search`)

## 동작

- 검색 완료 후 `/search/<결과 UUID>`로 이동합니다.
- 새로고침, 브라우저 뒤로/앞으로 가기, 검색 기록 클릭은 저장된 답변을 불러옵니다. AI를 다시 호출하지 않습니다.
- 설명 수준 변경과 새 질문은 새로운 답변과 주소를 생성합니다.
- 로그인 검색의 개인 주소는 해당 계정으로 로그인해야 열립니다.
- 비로그인 검색도 저장됩니다. 개인 주소는 검색했던 브라우저의 HttpOnly 쿠키로 접근하며, 쿠키는 비로그인 검색 시마다 30일로 갱신됩니다. 쿠키 삭제/만료 시 개인 주소 접근은 불가능합니다.
- **링크 공유**를 누르면 `/share/<별도의 UUID>`가 발급됩니다. 이 링크를 가진 사람은 로그인 없이 질문, 답변, 요약, 출처 및 이미지를 볼 수 있습니다. 공유 전에는 공개 주소가 없습니다.
- 공유 URL은 개인 결과 ID, 계정 정보, 내부 요청/대화 ID를 반환하지 않습니다. 검색엔진 색인 방지 헤더를 설정하지만 링크를 가진 사람의 재공유를 막지는 않습니다.
- 클립보드 복사가 불가능한 환경에서는 주소 입력란에서 직접 복사할 수 있습니다.
- 과거 검색 기록도 개인 링크와 공유를 지원합니다. 과거에 저장되지 않았던 요약은 복구할 수 없으며, 과거 기록의 이미지는 기존 출처 데이터로 조회합니다.

## 저장과 API

기존 `search_records` 및 사용자 기록 권한을 변경하지 않고 `search_results` 테이블에 화면에 필요한 답변 스냅샷을 추가 저장합니다. 로그인 검색의 두 저장 작업은 같은 트랜잭션으로 처리합니다.

| API | 접근 |
| --- | --- |
| `GET /api/v1/searches/<id>` | 작성 계정 또는 비로그인 브라우저 쿠키 |
| `POST /api/v1/searches/<id>/share` | 같은 소유권 검사 + 기존 CSRF 검사 |
| `GET /api/v1/shared-searches/<token>` | 공개, 명시적으로 공유된 결과만 |

공유는 같은 결과에 대해 동일한 링크를 반환합니다. 공유 취소/만료 및 비로그인 데이터 자동 정리는 이번 범위에 포함하지 않았습니다.

## 실행 및 배포

이 브랜치는 당시 커밋된 `main`에서 분리한 작업 폴더에 있습니다. 원래 작업 폴더의 미커밋 DB 정리 변경은 포함하지 않습니다. PR 준비 시 최신 main의 마이페이지와 검색 문맥 유지 변경을 통합했습니다.

1. 브랜치의 백엔드에 `python manage.py migrate`를 실행하여 `0006_search_result_links`를 적용합니다.
2. 프런트엔드를 다시 빌드하고 백엔드/프런트엔드 서비스를 갱신합니다.
3. HTTPS 배포의 `deploy/nginx-https.conf`도 반영합니다. SPA fallback은 직접 주소 접속을 지원하며, `/share/`는 noindex/no-referrer 헤더를 추가합니다.

현재 원래 작업 폴더에는 별도의 `0006` 이후 마이그레이션 작업이 있으므로, 그 작업과 합칠 때 마이그레이션 의존성을 먼저 정리해야 합니다. 이 브랜치에서 실제 배포나 운영 DB 마이그레이션은 수행하지 않았습니다.

## 검증

```sh
python backend/manage.py test api.link_tests --settings=config.search_links_test_settings
# PYTHONPATH=backend, DJANGO_SETTINGS_MODULE=config.test_settings
python -m unittest discover -s backend/api/tests -p "test_*.py"
cd frontend
npm test
npm run build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173
# 별도 터미널: Playwright 설치 필요. 환경에 따라 BROWSER_CHANNEL=chrome 지정 가능.
node scripts/check-search-links.mjs
```

브라우저 검증은 API 응답을 모의하여 화면/이동 동작을 검사합니다. 백엔드 접근권한/저장/공유는 별도의 실제 SQLite 통합 테스트로 검사합니다. SQLite 테스트는 기존 MySQL 전용 정리 마이그레이션 대신 현재 모델로 스키마를 구성합니다. 운영 MySQL에 대한 마이그레이션 실행 검증은 별도로 필요합니다.
