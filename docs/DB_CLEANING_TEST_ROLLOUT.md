# 테스트 DB 정리 적용

## 범위

서비스 테이블 8개와 django_migrations를 유지한다.
users, auth_sessions, search_records, search_citations, search_results,
error_reports, error_report_types, error_report_quotes가 서비스 테이블이다.

Django 기본 관리자·권한·세션 앱/미들웨어/컨텍스트 프로세서와 /admin/ 라우트를 제거한다.
자체 회원 인증과 /api/v1/admin 관리자 기능은 유지한다.
django_admin_log, django_session, auth_group_permissions, auth_permission,
auth_group, django_content_type 테이블을 의존 순서대로 제거한다.

신고 유형은 error_report_types에 저장하고 error_reports.category를 제거한다.
API는 기존 category 입력·응답을 계속 지원하며 categories와 selected_quotes도 지원한다.
기존 0006 마이그레이션 이력이 있는 복제본도 0007에서 누락된 단일 유형을 재확인하여 보존한다.
users.role, error_reports.handled_by_id, 신고 owner_id, 검색 결과 스냅샷은 유지한다.

## 검증

- SQLite 기반 스키마·회원·신고·관리자 테스트 8개, 검색 공유 테스트 8개 통과.
- 백엔드 단위 테스트 14개 통과.
- 독립 로컬 MySQL 복제본에서 15→9 전환, 서비스 행 수 보존, 모든 기존 category 보존 확인.
- makemigrations --check에서 변경 없음, 두 번째 migrate에서 추가 작업 없음.
- smoke_cleanup.py로 실제 MySQL의 가입/로그인/로그아웃/검색 이력/출처/공유/비회원/신고/관리자/탈퇴 검증.
  RAG는 stub으로 고정하고 쓰기는 트랜잭션 롤백한다. 외부 AI 생성 성공을 뜻하지 않는다.
- 로컬 전체 pytest는 전용 DB 검증 가상환경의 streamlit/requests/python-dotenv 등 미설치로 수집 불가.
  전체 의존성을 설치하는 PR CI 결과를 별도로 확인한다.

## 배포와 복구

운영 main/DB에는 적용하지 않는다. 테스트 PR preview로만 배포한다.
기존 테스트 배포 컨트롤러는 앱을 중지한 뒤 before-migrate.sql을 보관하고 migrate를 실행한다.
배포 후 테스트 DB 테이블 9개와 smoke_cleanup.py의 성공을 확인한다.

스키마 삭제는 역마이그레이션으로 자동 복구하지 않는다. 문제 발생 시 테스트 앱을 중지하고
변경 전 백업을 별도 빈 테스트 볼륨에 복원한 뒤 이전 코드와 함께 검증한다.
정리 전 main 코드는 category 컬럼을 사용하므로, 이 PR의 preview 라벨을 제거하거나 PR을 닫아
정리 전 main으로 되돌리지 않는다. 먼저 호환 코드 반영 또는 DB 백업 복원이 필요하다.
테스트 결과를 운영 DB에 역복사하지 않고 검증한 코드·마이그레이션만 추후 별도 승인 후 반영한다.
