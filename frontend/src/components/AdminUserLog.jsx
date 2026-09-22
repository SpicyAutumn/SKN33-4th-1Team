import { useEffect, useState } from "react";
import "./AdminUserLog.css";

const PAGE_SIZE = 20;
const dateLabel = (value) => new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));

export default function AdminUserLog({ api, onBack }) {
  const [page, setPage] = useState(0);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: "" });

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    api(`admin/users?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`)
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
  return <section className="admin-user-page"><div className="admin-user-shell">
    <button type="button" className="user-log-back" onClick={onBack}>← 운영 대시보드</button>
    <header className="user-log-heading"><p>사용자 접속</p><h1>최근 접속한 사용자</h1><span>사용자별 마지막 접속 시각을 기준으로 최근 순서로 표시합니다.</span></header>
    <section className="user-log-card">{state.loading ? <p className="user-log-state" role="status">접속 기록을 불러오고 있어요.</p> : state.error ? <p className="user-log-state user-log-error" role="alert">{state.error}</p> : state.items.length ? <><div className="user-log-summary"><span>총 {state.total}명</span><span>{start}–{end}명 표시</span></div><ul>{state.items.map((item) => <li key={item.id}><span className="user-log-avatar">{item.name.slice(0, 1)}</span><div><strong>{item.name}</strong><small>{item.email}</small></div><time>{dateLabel(item.last_seen_at)}</time></li>)}</ul><nav className="user-log-pages" aria-label="사용자 접속 목록 페이지"><button type="button" disabled={page === 0} onClick={() => changePage(-1)}>이전</button><span>{page + 1} / {Math.ceil(state.total / PAGE_SIZE)}</span><button type="button" disabled={end >= state.total} onClick={() => changePage(1)}>다음</button></nav></> : <p className="user-log-state">최근 접속 기록이 없습니다.</p>}</section>
  </div></section>;
}
