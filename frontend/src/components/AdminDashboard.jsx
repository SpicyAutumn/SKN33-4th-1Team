import { useEffect, useState } from "react";
import "./AdminDashboard.css";
import "./AdminDashboardSearchLinks.css";

const statusLabels = { received: "접수됨", reviewing: "확인 중", completed: "처리 완료" };
const levelLabels = { easy: "초등학생", general: "중·고등학생", advanced: "성인 일반" };
const dateLabel = (value) => new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));

export default function AdminDashboard({ api, onBack, onOpenUsers, onOpenReports, onOpenSearches, onOpenSearchDetail }) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: "" });
    api("admin/dashboard")
      .then((data) => { if (active) setState({ data, loading: false, error: "" }); })
      .catch((error) => { if (active) setState({ data: null, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, retry]);

  if (state.loading) return <section className="admin-dashboard-page"><p className="dashboard-state" role="status">운영 현황을 불러오고 있어요.</p></section>;
  if (state.error) return <section className="admin-dashboard-page"><div className="dashboard-state dashboard-error" role="alert"><p>{state.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button></div></section>;

  const { summary, recent_reports: reports, recent_users: users, recent_searches: searches } = state.data;
  return <section className="admin-dashboard-page"><div className="admin-dashboard-shell">
    <button type="button" className="dashboard-back" onClick={onBack}>← 서비스 화면으로</button>
    <header className="dashboard-heading"><div><p>관리자 전용</p><h1>운영 대시보드</h1><span>오류 제보와 서비스 이용 기록을 최근 순으로 확인합니다.</span></div><button type="button" className="primary" onClick={onOpenReports}>오류 제보 관리</button></header>
    <section className="dashboard-summary" aria-label="운영 현황 요약">
      <article><span>전체 오류 제보</span><strong>{summary.total_reports}</strong><small>누적 제보</small></article>
      <article className="received"><span>접수됨</span><strong>{summary.received_reports}</strong><small>확인 대기 제보</small></article>
      <article className="reviewing"><span>확인 중</span><strong>{summary.reviewing_reports}</strong><small>처리 진행 제보</small></article>
      <article className="completed"><span>처리 완료</span><strong>{summary.completed_reports}</strong><small>처리 완료 제보</small></article>
    </section>
    <section className="dashboard-grid">
      <article className="dashboard-card dashboard-reports"><header><div><p>오류 제보</p><h2>최근 접수된 제보</h2></div><button type="button" onClick={onOpenReports}>전체 관리 →</button></header>{reports.length ? <ul>{reports.map((item) => <li key={item.id}><span className={`dashboard-status status-${item.status}`}>{statusLabels[item.status] || item.status}</span><div><strong>{item.question_preview}</strong><small>{item.reporter_name} · {dateLabel(item.created_at)}</small></div></li>)}</ul> : <p className="dashboard-empty">등록된 오류 제보가 없습니다.</p>}</article>
      <article className="dashboard-card"><header><div><p>사용자 접속</p><h2>최근 접속한 사용자</h2></div><button type="button" onClick={onOpenUsers}>전체 보기 →</button></header>{users.length ? <ul>{users.map((item) => <li key={item.id}><span className="dashboard-avatar">{item.name.slice(0, 1)}</span><div><strong>{item.name}</strong><small>{item.email}</small></div><time>{dateLabel(item.last_seen_at)}</time></li>)}</ul> : <p className="dashboard-empty">최근 접속 기록이 없습니다.</p>}</article>
      <article className="dashboard-card dashboard-searches"><header><div><p>검색 기록</p><h2>최근 검색</h2></div><button type="button" onClick={onOpenSearches}>전체 보기 →</button></header>{searches.length ? <ul>{searches.map((item) => <li key={item.id}><button type="button" onClick={() => onOpenSearchDetail(item.id)}><div><strong>{item.question}</strong><small>{item.user_name} · {levelLabels[item.audience_level] || item.audience_level}</small></div><time>{dateLabel(item.created_at)}</time></button></li>)}</ul> : <p className="dashboard-empty">저장된 검색 기록이 없습니다.</p>}</article>
    </section>
  </div></section>;
}
