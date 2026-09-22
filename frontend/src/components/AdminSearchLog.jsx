import { useEffect, useState } from "react";
import "./AdminSearchLog.css";

const PAGE_SIZE = 20;
const levelLabels = { easy: "초등학생", general: "중·고등학생", advanced: "성인 일반" };
const dateLabel = (value) => new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));

export default function AdminSearchLog({ api, onBack }) {
  const [page, setPage] = useState(0);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: "" });

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    api(`admin/searches?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`)
      .then((data) => { if (active) setState({ items: data.items || [], total: data.total || 0, loading: false, error: "" }); })
      .catch((error) => { if (active) setState({ items: [], total: 0, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, page]);

  const start = state.total ? page * PAGE_SIZE + 1 : 0;
  const end = Math.min((page + 1) * PAGE_SIZE, state.total);
  const changePage = (direction) => {
    setPage((value) => value + direction);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return <section className="admin-search-page"><div className="admin-search-shell">
    <button type="button" className="search-log-back" onClick={onBack}>← 운영 대시보드</button>
    <header className="search-log-heading"><p>검색 기록</p><h1>전체 검색 기록</h1><span>사용자가 질문한 내용과 검색 시각을 최근 순서로 확인할 수 있습니다.</span></header>
    <section className="search-log-card">{state.loading ? <p className="search-log-state" role="status">검색 기록을 불러오고 있어요.</p> : state.error ? <p className="search-log-state search-log-error" role="alert">{state.error}</p> : state.items.length ? <><div className="search-log-summary"><span>총 {state.total}건</span><span>{start}–{end}건 표시</span></div><ul>{state.items.map((item) => <li key={item.id}><div><strong>{item.question}</strong><small>{item.user_name} · {item.user_email} · {levelLabels[item.audience_level] || item.audience_level}</small></div><time>{dateLabel(item.created_at)}</time></li>)}</ul><nav className="search-log-pages" aria-label="검색 기록 페이지"><button type="button" disabled={page === 0} onClick={() => changePage(-1)}>이전</button><span>{page + 1} / {Math.ceil(state.total / PAGE_SIZE)}</span><button type="button" disabled={end >= state.total} onClick={() => changePage(1)}>다음</button></nav></> : <p className="search-log-state">저장된 검색 기록이 없습니다.</p>}</section>
  </div></section>;
}
