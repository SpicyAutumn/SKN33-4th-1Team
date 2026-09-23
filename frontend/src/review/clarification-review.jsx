// Development only: the real App serializes requests to this in-memory stub.
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import App from '../App';
import '../styles.css';

function Review() {
  const [version, setVersion] = useState(0);
  const [requests, setRequests] = useState([]);
  const [request] = useState(() => async (path, options = {}) => {
    if (path === 'auth/me') throw new Error('검증용 비로그인 상태');
    if (path !== 'searches') throw new Error('검증 화면에서 지원하지 않는 요청');
    const body = JSON.parse(options.body);
    setRequests((old) => [...old, body]);
    // Keep the choice screen available so selection and editing can be repeated.
    return { request_id: `review-${Date.now()}`, interaction_id: 'INT-review',
      response_type: 'needs_clarification', message: '어느 이순신을 말씀하시나요?', citations: [],
      clarification: { reason_code: 'ambiguous_entity', question: '탐색할 인물을 선택해 주세요.', options: [
        { id: 'first', label: '충무공 이순신', source_chunk_ids: ['aks:review:first'] },
        { id: 'second', label: '선무공신 이순신', source_chunk_ids: ['aks:review:second'] },
      ] } };
  });
  return <><aside style={{ padding: 16, background: '#fff0c9' }}>
    <b>추가 질문 통합 검증 · 실제 AI/DB 미사용</b>
    <p>이순신 장군을 검색한 후 두 번째 선택지와 직접 문장 수정 흐름을 확인합니다.</p>
    <button onClick={() => { setVersion((old) => old + 1); setRequests([]); }}>검증 초기화</button>
    <details open><summary>App이 전송한 요청 내용</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(requests, null, 2)}</pre></details>
  </aside><App key={version} request={request} /></>;
}
createRoot(document.getElementById('root')).render(<Review />);
