import { useEffect, useState } from "react";
import "./AdminSearchLog.css";

const PAGE_SIZE = 20;
const levelLabels = { easy: "초등학생", general: "중·고등학생", advanced: "성인 일반" };
const dateLabel = (value) => new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));

export default function AdminSearchLog({ api, onBack }) {
  const [page, setPage] = useState(0);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: "" });
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState({ item: null, loading: false, error: "" });

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    api(`admin/searches?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`)
      .then((data) => { if (active) setState({ items: data.items || [], total: data.total || 0, loading: false, error: "" }); })
      .catch((error) => { if (active) setState({ items: [], total: 0, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, page]);

  useEffect(() => {
    if (!selectedId) { setDetail({ item: null, loading: false, error: "" }); return undefined; }
    let active = true;
    setDetail({ item: null, loading: true, error: "" });
    api(`admin/searches/${encodeURIComponent(selectedId)}`).then((item) => {
      if (active) setDetail({ item, loading: false, error: "" });
    }).catch((error) => { if (active) setDetail({ item: null, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, selectedId]);

  const start = state.total ? page * PAGE_SIZE + 1 : 0;
  const end = Math.min((page + 1) * PAGE_SIZE, state.total);
  const changePage = (direction) => {
    setSelectedId(null); setPage((value) => value + direction);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return <section className="admin-search-page"><div className="admin-search-shell">
    <button type="button" className="search-log-back" onClick={onBack}>← 운영 대시보드</button>
    <header className="search-log-heading"><p>검색 기록</p><h1>전체 검색 기록</h1><span>사용자가 질문한 내용과 검색 시각을 최근 순서로 확인할 수 있습니다.</span></header>
    {selectedId && <section className="search-detail" aria-live="polite">{detail.loading ? <p className="search-log-state" role="status">검색기록 전문을 불러오고 있어요.</p> : detail.error ? <div className="search-log-state search-log-error" role="alert"><p>{detail.error}</p><button type="button" onClick={() => setSelectedId(null)}>목록으로</button></div> : detail.item && <><header><div><p>검색기록 전문</p><h2>{detail.item.question}</h2></div><button type="button" onClick={() => setSelectedId(null)}>목록으로</button></header><dl><div><dt>사용자</dt><dd>{detail.item.user_name} · {detail.item.user_email}</dd></div><div><dt>난이도</dt><dd>{levelLabels[detail.item.audience_level] || detail.item.audience_level}</dd></div><div><dt>검색 시각</dt><dd>{dateLabel(detail.item.created_at)}</dd></div></dl><section><h3>AI 답변 전문</h3><p className="search-detail-message">{detail.item.message}</p></section>{detail.item.citations.length > 0 && <section><h3>출처 {detail.item.citations.length}건</h3><ol>{detail.item.citations.map((citation) => <li key={citation.chunk_id}><strong>{citation.title}</strong>{citation.section && <span>{citation.section}</span>}{citation.source_url && <a href={citation.source_url} target="_blank" rel="noreferrer">원문 보기</a>}</li>)}</ol></section>}</>}</section>}
    <section className="search-log-card">{state.loading ? <p className="search-log-state" role="status">검색 기록을 불러오고 있어요.</p> : state.error ? <p className="search-log-state search-log-error" role="alert">{state.error}</p> : state.items.length ? <><div className="search-log-summary"><span>총 {state.total}건</span><span>{start}–{end}건 표시</span></div><ul>{state.items.map((item) => <li key={item.id}><button type="button" className={selectedId === item.id ? "selected" : ""} onClick={() => setSelectedId(item.id)}><div><strong>{item.question}</strong><small>{item.user_name} · {item.user_email} · {levelLabels[item.audience_level] || item.audience_level}</small></div><time>{dateLabel(item.created_at)}</time><b aria-hidden="true">›</b></button></li>)}</ul><nav className="search-log-pages" aria-label="검색 기록 페이지"><button type="button" disabled={page === 0} onClick={() => changePage(-1)}>이전</button><span>{page + 1} / {Math.ceil(state.total / PAGE_SIZE)}</span><button type="button" disabled={end >= state.total} onClick={() => changePage(1)}>다음</button></nav></> : <p className="search-log-state">저장된 검색 기록이 없습니다.</p>}</section>
  </div></section>;
}
