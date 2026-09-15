# `feature/django-web-auth` 브랜치 안내

이 브랜치는 문화유산 AI 가이드의 **Django 기반 회원 기능**을 추가합니다.

## 포함된 기능

- 이메일, 아이디, 비밀번호를 받는 회원가입
- 아이디 또는 이메일로 로그인
- 로그아웃 및 현재 로그인 회원 조회
- Django의 비밀번호 해시 저장
- MySQL 공용 DB에 회원 정보 저장
- Django migration을 통한 회원 테이블 생성

회원 기능 API는 다음 주소를 제공합니다.

| 메서드 | 주소 | 설명 |
| --- | --- | --- |
| `GET` | `/accounts/api/csrf/` | CSRF 쿠키 발급 |
| `POST` | `/accounts/api/signup/` | 회원가입 |
| `POST` | `/accounts/api/login/` | 로그인 |
| `POST` | `/accounts/api/logout/` | 로그아웃 |
| `GET` | `/accounts/api/me/` | 현재 로그인 회원 조회 |

## 포함하지 않는 범위

- 최종 피그마 UI 및 화면 배치
- React 화면과 API를 연결하는 프론트엔드 코드
- RAG 질문·답변 기능

UI가 확정된 뒤에는 프론트엔드에서 위 API를 호출하는 별도 작업을 진행합니다.

## 팀 공유 DB 설정

실행 전 `django_web/.env.example`을 참고해 각자의 `django_web/.env` 파일을 만듭니다.

```env
DJANGO_SECRET_KEY=각자_생성한_비밀키
DB_NAME=django_project4
DB_USER=root
DB_PASSWORD=
DB_HOST=skn33.iptime.org
DB_PORT=33061
```

`.env`는 비밀키와 DB 비밀번호를 담을 수 있으므로 Git에 올리지 않습니다.

## 최초 실행

```powershell
cd django_web
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`migrate`는 Django의 회원 테이블을 공용 `django_project4` DB에 생성하거나 최신 상태로 맞춥니다.

## 공용 로그인 확인 계정

아래 계정은 팀원이 공용 DB 연결과 로그인을 확인하기 위한 **개발 전용 계정**입니다.
개인 서비스나 실제 배포 환경에서는 사용하지 않습니다.

```text
아이디: 킹세종
이메일: aaaa@gmail.com
비밀번호: aaaa1234
```

## 검증 결과

- Django 회원가입·로그인 테스트 4건 통과
- 피그마 UI에서 가입한 계정이 공용 DB에 저장되는 것 확인
- 최신 `main` 기준 병합 충돌 없음
