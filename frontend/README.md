# Figma 화면 프런트엔드

Figma Make의 문화유산 AI 가이드 화면을 React로 옮긴 웹 프런트엔드입니다.
기존 `app/`과 `src/`의 RAG 로직을 바꾸지 않고, `api/main.py`를 통해서만
답변을 요청합니다.

## 처음 한 번만

프로젝트 루트에서 Python 의존성을 설치합니다.

```powershell
<python 실행파일> -m pip install -r requirements.txt
```

프런트엔드 의존성도 설치합니다.

```powershell
cd frontend
npm install
```

## 실행

터미널을 두 개 엽니다.

첫 번째 터미널에서는 프로젝트 루트에서 API를 실행합니다.

```powershell
<python 실행파일> -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

두 번째 터미널에서는 프런트엔드를 실행합니다.

```powershell
cd frontend
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`을 엽니다.

## 현재 연결 범위

- 질문 → `POST /api/ask` → 기존 RAG 응답·근거 카드
- 문화유산 상세 → `GET /api/heritages/gyeongbokgung`
- 오류 제보 → `POST /api/reports` (현재 서버 메모리 보관)
- 최근 질문·저장 목록·시연 로그인 → 브라우저 `localStorage`

실제 회원가입·로그인·다기기 동기화는 DB와 인증 API를 추가하는 다음 단계에서
연결합니다. RAG 패키지 또는 키 설정이 없는 개발 환경에서는 질문 화면이
시연 응답을 보여 주며, 실제 오류 내용이나 환경변수 값은 브라우저에 노출하지
않습니다.
