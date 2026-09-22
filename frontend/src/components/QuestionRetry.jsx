import { useId, useState } from 'react';
import './QuestionRetry.css';

export default function QuestionRetry({ question, result, onAsk, busy }) {
  const [value, setValue] = useState(question);
  const inputId = useId();
  const clarify = result.response_type === 'needs_clarification';
  const options = Array.isArray(result.clarification?.options) ? result.clarification.options : [];
  return <section className="question-retry" aria-label="질문을 바꾸어 다시 검색">
    <h2>{clarify ? '질문을 조금 더 구체적으로 알려주세요' : '질문을 바꾸어 다시 찾아보세요'}</h2>
    <p>{clarify ? result.clarification?.question || '대상 이름이나 확인할 내용을 입력해 주세요.' : '이번 검색에서는 답변에 필요한 근거를 찾지 못했어요. 대상 이름·지역·궁금한 특징을 구체적으로 적어 주세요.'}</p>
    {clarify && options.length > 0 && <div className="question-retry-options">{options.filter((option) => typeof option?.label === 'string' && option.label.trim()).map((option, index) => <button key={option.id || index} type="button" disabled={busy} onClick={() => { setValue(result.clarification?.reason_code === "compound_question" ? option.label : `${question} (${option.label})`); document.getElementById(inputId)?.focus(); }}>{option.label}</button>)}</div>}
    <form onSubmit={(event) => { event.preventDefault(); if (!busy && value.trim() && value.trim().length <= 1000) onAsk(value.trim()); }}>
      <label htmlFor={inputId}>다시 검색할 질문</label>
      <textarea id={inputId} value={value} onChange={(event) => setValue(event.target.value)} required maxLength={1000} rows={2} disabled={busy} />
      <div className="question-retry-submit"><small>수정한 내용을 새 질문으로 검색합니다.</small><button type="submit" disabled={busy || !value.trim()}>이 질문으로 다시 검색</button></div>
    </form>
  </section>;
}
