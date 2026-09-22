// Development-only entry. Not imported by main.jsx or included in the production build.
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import App, { AnswerView } from '../App';
import photos from '../data/heritagePhotos.json';
import '../styles.css';

const records = [
  { id: 'review-1', question: '경복궁 근정전은 어떤 곳인가요?', audience_level: 'general', created_at: '2026-09-18T01:30:00Z', message: '저장 당시 답변 예시입니다. 근정전은 국가의 중요한 의식을 치르던 건물입니다.', response_type: 'answered', citations: [{ title: '경복궁 근정전', source_url: 'https://encykorea.aks.ac.kr/Article/E0002442', content: '검증용 근거 예시입니다.' }] },
  { id: 'review-2', question: '수원 화성의 건축 과정과 역사적 의미를 아주 긴 질문으로 다시 확인해 보고 싶어요', audience_level: 'easy', created_at: '2026-09-17T06:00:00Z', message: '수원 화성 저장 답변 예시입니다.', response_type: 'answered', citations: [] },
  { id: 'review-missing', question: '삭제되었거나 접근할 수 없는 기록', audience_level: 'general', created_at: '2026-09-16T06:00:00Z' },
];

function Review() {
  const [mode, setMode] = useState('normal');
  const [preview, setPreview] = useState('app');
  const photo = photos.find((item) => item.id === 'seoul');
  const photoCitation = { ...records[0].citations[0], document_id: 'aks:E0002442' };
  const previewResult = { ...records[0], search_record_id: 'review-1', summary: '화면 검증용 요약입니다.', citations: [photoCitation], media: preview === 'photo' || preview === 'broken' ? [{ document_id: 'aks:E0002442', article_title: photo.name, images: [{ ...photo, url: new URL(preview === 'broken' ? '/heritage/missing-test.jpg' : photo.image, window.location.origin).href }] }] : [] };
  const [calls, setCalls] = useState([]);
  const [request] = useState(() => async (path, options = {}) => {
    const method = options.method || 'GET';
    setCalls((items) => [...items, `${method} ${path}`]);
    if (method !== 'GET') throw new Error('검증 화면에서는 쓰기·답변 생성 요청을 차단했습니다.');
    if (path === 'auth/csrf') return {};
    if (path === 'auth/me') return { id: 'review-user', name: '검증용 사용자' };
    if (path.startsWith('me/searches?')) return { items: records, next_cursor: null };
    const record = records.find((item) => path === `me/searches/${item.id}`);
    if (!record?.message) throw new Error('검색 기록을 찾을 수 없습니다.');
    return record;
  });
  const [emptyRequest] = useState(() => (path, options) => path.startsWith('me/searches?') ? Promise.resolve({ items: [] }) : request(path, options));
  const [failedRequest] = useState(() => (path, options) => path.startsWith('me/searches?') ? Promise.reject(new Error('기록 목록을 불러오지 못했습니다.')) : request(path, options));
  return <><aside style={{ padding: 16, background: '#fff0c9' }}><b>전체 UI 최신 테스트 · 실제 API/DB 미사용</b><p>메인·검색 기록·답변 사진·오류 제보와 최신 시도 지도 로딩을 확인합니다. 아래 화면 확인에서 선택해 주세요.</p>
    <label>검증 상황 <select value={mode} onChange={(event) => setMode(event.target.value)}><option value="normal">기록 있음</option><option value="empty">기록 없음</option><option value="failed">목록 조회 실패</option></select></label>
    <p><label>화면 확인 <select value={preview} onChange={(event) => setPreview(event.target.value)}><option value="app">메인·검색 기록</option><option value="loading">답변 준비 중</option><option value="photo">사진 있는 답변</option><option value="no-photo">사진 없는 답변</option><option value="broken">사진 로드 실패</option><option value="report-v2">PR #20 오류 제보</option><option value="report-fail">오류 제보 전송 실패</option></select></label></p>
    <details><summary>검증 요청 내역</summary><pre>{calls.join('\n')}</pre></details></aside>
    {preview === "app" ? <App key={mode} request={mode === 'empty' ? emptyRequest : mode === 'failed' ? failedRequest : request} /> : <AnswerView capturePreview key={preview} question={records[0].question} level="general" result={preview === "loading" ? null : previewResult} loading={preview === "loading"} loadingRecord={false} onBack={() => setPreview("app")} onChangeLevel={() => {}} reportMode={preview === "report-v2" ? "v2" : "legacy"} onSubmitReport={async (payload) => { setCalls((items) => [...items, "가상 제보: " + JSON.stringify(payload)]); if (preview === "report-fail") throw new Error("검증용 전송 실패: 입력 내용을 유지합니다."); }} onAsk={() => {}} />}
  </>;
}
createRoot(document.getElementById('root')).render(<Review />);
