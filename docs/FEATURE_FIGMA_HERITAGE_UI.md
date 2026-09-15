# `feature/figma-heritage-ui` 브랜치 안내

이 브랜치는 피그마 시안을 바탕으로 만든 **React 기반 문화유산 AI 가이드 화면**을 추가합니다.

## 포함된 화면과 기능

- 문화유산 AI 가이드 홈 화면
- 문화유산 둘러보기, 오늘의 이야기, 내 기록 화면 흐름
- 질문 입력, 설명 수준 선택, 최근 검색·저장 목록·오류 제보 UI
- 로그인·회원가입·마이페이지 UI
- 반응형 CSS와 Vite 개발 서버 설정

## Django 회원 기능 연결

이 UI는 회원 기능을 직접 구현하지 않습니다. 대신 Django 백엔드의 API를 호출합니다.

```text
React UI (5173)
  → /django-api 프록시
  → Django 인증 서버 (8011)
  → 팀 공유 MySQL DB
```

로그인, 회원가입, 로그아웃, 현재 로그인 회원 조회는 `feature/django-web-auth` 브랜치의 Django API를 사용합니다.
따라서 실제 회원 기능을 사용하려면 해당 브랜치가 먼저 병합되어 있거나, 로컬에서 Django 서버가 실행 중이어야 합니다.

## 실행 방법

```powershell
cd frontend
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:5173/`를 엽니다.

회원 기능까지 확인하려면 별도 터미널에서 Django 인증 서버를 실행합니다.

```powershell
cd django_web
python manage.py runserver 127.0.0.1:8011
```

## 검증 결과

- `npm run build` 성공
- `5173 → Django API → 공용 DB` 경로로 로그인·현재 사용자 조회·로그아웃 성공
- 최신 `main`을 기준으로 UI 변경 파일의 병합 충돌 없음

## 포함하지 않는 범위

- Django 회원 모델, DB migration, 인증 API 구현
- RAG 실제 답변 연결
- 최종 서비스 배포 설정

## 병합 순서

1. `feature/django-web-auth` 병합
2. `feature/figma-heritage-ui` 병합

이 순서면 UI가 호출하는 Django 인증 API를 즉시 사용할 수 있습니다.
