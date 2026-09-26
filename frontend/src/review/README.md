# 개발용 화면 검증

모의 응답 화면입니다. 제품 컴포넌트는 재사용하지만 제품 진입점 `src/main.jsx`에서 이 폴더를 import하지 않습니다.

`frontend/`에서 `npm run dev`를 실행한 뒤 표시된 주소에 다음 경로를 붙입니다.

| 경로 | 확인하는 동작 |
|---|---|
| `/clarification-review.html` | 되묻기 선택과 요청 문맥 |
| `/history-review.html` | 기록·사진·제보·응답 중복·전송 실패 |
| `/mypage-review.html` | 긴 검색 기록과 좁은 화면 |
| `/network-review.html` | 연관 탐색 실패·재시도·초기화 |
| `/recommendation-review.html` | 추천 근거와 다음 질문 전달 |

제보 검증은 현재 제품의 단일 유형·설명 규칙 또는 서버가 지원하는 `v2` 규칙을 사용합니다. 과거 시안의 미지원 유형·설명 생략 옵션은 제품 코드에서 제거했습니다. `ReportCapturePreview.jsx`와 전용 CSS는 기록 화면의 별도 시안 영역에서만 사용하며 이미지를 서버에 전송하지 않습니다. [과거 사양](../../../docs/archive/ui/ERROR_REPORT_UI_SPEC.md)은 보관합니다.

실제 로컬 Docker API와 연결해 제품 화면을 확인할 때는 `npm exec vite -- --config vite.review.config.js`를 사용합니다. `127.0.0.1:5174`에서 `127.0.0.1:8081`의 API로 연결하므로 모의 응답 화면과 구분하며 Docker 서비스가 먼저 실행돼 있어야 합니다.
