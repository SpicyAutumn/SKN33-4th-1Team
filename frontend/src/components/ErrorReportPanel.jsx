import { useEffect, useRef, useState } from 'react';
import { reportPayload, reportTypes, previewReportTypes } from './reportPayload';
import './ErrorReportPanel.css';
import ReportCapturePreview from './ReportCapturePreview';

export default function ErrorReportPanel({ recordId, answer, answerRef, mode = 'legacy', capturePreview = false, onSubmit, onOpenChange }) {
  const [open, setOpen] = useState(false);
  const availableTypes = capturePreview && mode !== 'v2' ? previewReportTypes : reportTypes;
  const [collapsed, setCollapsed] = useState(false);
  const [categories, setCategories] = useState([]);
  const [content, setContent] = useState('');
  const [quotes, setQuotes] = useState([]);
  const [candidate, setCandidate] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const title = useRef(null);
  const launcher = useRef(null);
  const returnFocus = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; onOpenChange(false); }; }, [onOpenChange]);
  useEffect(() => {
    const capture = () => {
      const selection = window.getSelection();
      const element = answerRef.current;
      if (!element || !selection?.rangeCount || selection.isCollapsed) return;
      const range = selection.getRangeAt(0);
      if (!element.contains(range.startContainer) || !element.contains(range.endContainer)) return;
      const prefix = range.cloneRange(); prefix.selectNodeContents(element); prefix.setEnd(range.startContainer, range.startOffset);
      const text = range.toString();
      const start = Array.from(prefix.toString()).length;
      if (text.trim()) setCandidate({ text, start_offset: start, end_offset: start + Array.from(text).length });
    };
    document.addEventListener('selectionchange', capture);
    return () => document.removeEventListener('selectionchange', capture);
  }, [answerRef]);
  useEffect(() => { if (open && !collapsed) title.current?.focus({ preventScroll: true }); }, [open, collapsed]);
  useEffect(() => {
    if (!open && returnFocus.current) { launcher.current?.focus({ preventScroll: true }); returnFocus.current = false; }
  }, [open]);
  const close = () => { if (busy) return; returnFocus.current = true; setOpen(false); onOpenChange(false); };
  const addQuote = () => {
    if (!candidate) return;
    setError('');
    if (mode !== 'v2') {
      const next = `${content}${content ? '\n\n' : ''}선택한 문구: ${candidate.text}`;
      if (Array.from(next).length > 2000) { setError('설명은 선택 문구를 포함해 2,000자 이내로 작성해 주세요.'); return; }
      setContent(next);
    } else {
      if (quotes.some((quote) => quote.start_offset === candidate.start_offset && quote.end_offset === candidate.end_offset)) return;
      if (quotes.length >= 5 || Array.from(candidate.text).length > 2000) { setError('문구는 최대 5개, 각각 2,000자까지 추가할 수 있습니다.'); return; }
      setQuotes((items) => [...items, candidate]);
    }
    setCandidate(null);
  };
  const submit = async (event) => {
    event.preventDefault(); if (submitting.current) return;
    setError('');
    try {
      const payload = reportPayload({ recordId, categories, content, quotes, answer, mode, optionalDescriptionPreview: capturePreview });
      submitting.current = true; setBusy(true);
      await onSubmit(payload);
      if (alive.current) { setSuccess(true); setContent(''); setQuotes([]); setCandidate(null); }
    } catch (failure) { if (alive.current) setError(failure.message); }
    finally { submitting.current = false; if (alive.current) setBusy(false); }
  };
  return <>
    {!open && <button ref={launcher} type="button" className="report-launcher" onClick={() => { setOpen(true); setCollapsed(false); setSuccess(false); onOpenChange(true); }}>답변 오류 제보</button>}
    {open && <aside className={`report-dock${collapsed ? ' is-collapsed' : ''}`} aria-label="답변 오류 제보" onKeyDown={(event) => { if (event.key === 'Escape') close(); }}>
      <header><h2 ref={title} tabIndex={-1}>답변 오류 제보</h2><button type="button" onClick={() => { setCollapsed(!collapsed); onOpenChange(collapsed); }}>{collapsed ? '펼치기' : '접기'}</button><button type="button" disabled={busy} onClick={close}>닫기</button></header>
      {!collapsed && (success ? <p role="status">제보가 접수되었습니다.</p> : <form onSubmit={submit}>
        <p className="report-help">질문·답변은 자동 연결됩니다. 본문을 드래그해 문제 문구를 추가하세요.</p>
        {mode !== 'v2' ? <div className="report-category-select"><label htmlFor="report-category">오류 유형 (필수)</label><select id="report-category" disabled={busy} value={categories[0] || ''} onChange={event => setCategories(event.target.value ? [event.target.value] : [])}><option value="">오류 유형을 선택해 주세요</option>{availableTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div> : <fieldset disabled={busy}><legend>오류 유형 {mode === 'v2' ? '(여러 개 선택 가능)' : '(1개 선택)'}</legend>{availableTypes.map(([value, label]) => <label className="report-type" key={value}><input type={mode === 'v2' ? 'checkbox' : 'radio'} name="report-category" checked={categories.includes(value)} onChange={(event) => setCategories(mode !== 'v2' ? [value] : event.target.checked ? [...categories, value] : categories.filter((item) => item !== value))} /><span className="report-type-text">{label}</span></label>)}</fieldset>}
        <div className="report-quote-tools"><button type="button" disabled={busy || !candidate} onMouseDown={(event) => event.preventDefault()} onClick={addQuote}>{mode === 'v2' ? '선택 문구 추가' : '선택 문구를 설명에 추가'}</button>{candidate && <p>선택: {candidate.text}</p>}</div>
        {quotes.map((quote, index) => <div className="report-quote" key={`${quote.start_offset}-${quote.end_offset}`}><blockquote>{quote.text}</blockquote><button type="button" disabled={busy} aria-label={`선택 문구 ${index + 1} 삭제`} onClick={() => setQuotes(quotes.filter((_, i) => i !== index))}>삭제</button></div>)}
        <label className="report-content-label" htmlFor="report-content">추가 설명 {capturePreview && mode !== 'v2' ? (categories.includes('other') ? '(필수)' : '(선택)') : '(필수 조건은 아래 안내 참고)'}</label><textarea id="report-content" aria-required={capturePreview && categories.includes('other')} disabled={busy} value={content} onChange={(event) => setContent(event.target.value)} aria-describedby="report-rule" />
        <p id="report-rule" className="report-help">{capturePreview && mode !== 'v2' ? '기타 유형을 선택한 경우에만 추가 설명이 필수입니다.' : mode === 'v2' ? '선택 문구가 없거나 기타 유형이면 10자 이상 필요합니다.' : '선택 문구를 포함해 10자 이상 작성해 주세요.'} 최대 2,000자 · 현재 {Array.from(content.trim()).length}자</p>
        {capturePreview && <ReportCapturePreview />}
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit" className="primary" disabled={busy}>{busy ? '보내는 중…' : '제보 보내기'}</button>
      </form>)}
    </aside>}
  </>;
}
