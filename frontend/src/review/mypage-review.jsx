// Offline fixture: all application requests are mocked; no account changes or AI calls.
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from '../App';
import '../styles.css';

const records = [
  { id: 'long', question: '이순신과 임진왜란의 역사적 배경을 설명해 주세요. '.repeat(12) },
  { id: 'unbroken', question: '공백없는긴질문'.repeat(45) },
].map(record => ({ ...record, audience_level: 'general', created_at: '2026-09-22T01:00:00Z',
  response_type: 'answered', message: '검증용 저장 답변입니다.', citations: [] }));
async function request(path, options = {}) {
  if (path === 'auth/csrf') return {};
  if (path === 'auth/me') return { id: 'test', name: '검증 사용자', email: 'test@example.invalid' };
  if (path.startsWith('me/searches?')) return { items: records };
  const record = records.find(record => path === `me/searches/${record.id}`);
  if (record) return record;
  if (path === 'searches') {
    const payload = JSON.parse(options.body);
    document.getElementById('request-log').textContent = JSON.stringify(payload);
    if (!payload.selected_source_chunk_ids?.length && payload.question === '이순신 장군') {
      return { response_type: 'needs_clarification', message: '인물을 선택해 주세요.', interaction_id: 'test-interaction',
        clarification: { reason_code: 'ambiguous_entity', question: '인물을 선택해 주세요.',
          options: [{ id: 'person', label: '이순신 — 삼도수군통제사', source_chunk_ids: ['test-selected'] }] } };
    }
    return { ...records[0], request_id: String(Date.now()), question: payload.question };
  }
  throw new Error('검증에서 지원하지 않는 요청입니다.');
}
createRoot(document.getElementById('root')).render(<><p>모의 데이터 검증 · AI/DB 호출 없음</p><output id="request-log" style={{ display: 'block', overflowWrap: 'anywhere' }} /><App request={request} /></>);
