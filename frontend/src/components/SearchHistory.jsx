import { useEffect, useState } from 'react';
import './SearchHistory.css';

const dateLabel = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '날짜 미제공' : new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date);
};

export default function SearchHistory({ api, refreshKey, onOpen, busy, expanded = false, onMore, onBack }) {
  const [state, setState] = useState({ items: [], loading: true, error: '' });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ items: [], loading: true, error: '' });
    api(`me/searches?limit=${expanded ? 100 : 5}`).then(({ items }) => {
      if (active) setState({ items: items || [], loading: false, error: '' });
    }).catch((error) => {
      if (active) setState({ items: [], loading: false, error: error.message });
    });
    return () => { active = false; };
  }, [api, refreshKey, expanded, retry]);
  return <section className="search-history" aria-label="내 검색 기록">
    <div className="history-heading"><h2>{expanded ? '나의 검색 기록' : '내 검색 기록'}</h2>
      {expanded ? (onBack && <button type="button" onClick={onBack}>이전 화면</button>) : <button type="button" onClick={onMore}>기록 더 보기</button>}
    </div>
    <p className="history-caption">{expanded ? '최근 100건까지 표시합니다. 기록을 선택하면 저장 당시의 답변이 열립니다.' : '최근 5건 · 저장된 답변 다시 보기'}</p>
    {state.loading ? <p role="status">기록을 불러오고 있어요.</p> : state.error ? <div role="alert"><p>{state.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button></div> : state.items.length ? <ul>{state.items.map((item) => <li key={item.id}>
      <button type="button" disabled={busy} onClick={() => onOpen(item)}><span>{item.question}</span><time dateTime={item.created_at}>{dateLabel(item.created_at)}</time></button>
    </li>)}</ul> : <p>아직 저장된 검색 기록이 없습니다.</p>}
  </section>;
}
