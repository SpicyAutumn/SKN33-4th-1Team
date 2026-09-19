import { useEffect, useState } from "react";
import "./ErrorReportBoard.css";

const categoryLabels = { incorrect_fact: "사실이 틀림", citation_mismatch: "출처가 맞지 않음", incomplete_answer: "설명이 부족함", inappropriate_content: "부적절한 내용", other: "기타" };
const statusLabels = { received: "접수됨", reviewing: "확인 중", in_review: "확인 중", completed: "처리 완료", resolved: "처리 완료" };
const filters = [["all", "전체"], ["received", "접수됨"], ["reviewing", "확인 중"], ["completed", "처리 완료"]];

const dateLabel = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 미제공" : new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", year: "numeric", month: "long", day: "numeric" }).format(date);
};
const statusKey = (status) => ["reviewing", "in_review"].includes(status) ? "reviewing" : ["completed", "resolved"].includes(status) ? "completed" : "received";

export default function ErrorReportBoard({ api, onBack }) {
  const [state, setState] = useState({ items: [], loading: true, error: "" });
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState({ item: null, loading: false, error: "" });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ items: [], loading: true, error: "" });
    api("me/error-reports").then(({ items }) => { if (active) setState({ items: items || [], loading: false, error: "" }); }).catch((error) => { if (active) setState({ items: [], loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, retry]);
  const openDetail = async (item) => {
    if (!item) return;
    setSelected(item.id); setDetail({ item: null, loading: true, error: "" });
    try { setDetail({ item: await api(`me/error-reports/${encodeURIComponent(item.id)}`), loading: false, error: "" }); }
    catch (error) { setDetail({ item: null, loading: false, error: error.message }); }
  };
  const filteredItems = filter === "all" ? state.items : state.items.filter((item) => statusKey(item.status) === filter);
  if (selected) {
    const report = detail.item;
    return <section className="report-board-page"><div className="report-board-shell">
      <button type="button" className="board-back" onClick={() => { setSelected(null); setDetail({ item: null, loading: false, error: "" }); }}>← 오류 제보 게시판</button>
      {detail.loading && <p className="board-state" role="status">제보 내용을 불러오고 있어요.</p>}
      {detail.error && <div className="board-state board-error" role="alert"><p>{detail.error}</p><button type="button" onClick={() => openDetail(state.items.find((item) => item.id === selected))}>다시 시도</button></div>}
      {report && <article className="report-detail-card">
        <div className="report-detail-heading"><div><span className="report-category">{categoryLabels[report.category] || report.category}</span><h1>{report.question}</h1></div><span className={`report-status status-${statusKey(report.status)}`}>{statusLabels[report.status] || report.status}</span></div>
        <section><h2>제보 내용</h2><p className="report-detail-content">{report.content}</p></section>
        <section><h2>처리 현황</h2><ol className="report-progress"><li className="done">접수됨</li><li className={statusKey(report.status) === "reviewing" || statusKey(report.status) === "completed" ? "done" : ""}>확인 중</li><li className={statusKey(report.status) === "completed" ? "done" : ""}>처리 완료</li></ol></section>
        <section><h2>담당자 답변</h2><p className="staff-reply">{report.staff_reply || "담당자가 내용을 확인하고 있습니다."}</p></section>
        <details className="report-original-answer"><summary>제보 당시 AI 답변 <span>펼치기</span></summary><p>{report.answer_text || report.answer_preview}</p></details><time dateTime={report.created_at}>등록일 · {dateLabel(report.created_at)}</time>
      </article>}
    </div></section>;
  }
  return <section className="report-board-page"><div className="report-board-shell">
    <button type="button" className="board-back" onClick={onBack}>← 홈으로</button>
    <header className="report-board-heading"><div><p>나의 오류 제보</p><h1>오류 제보 게시판</h1><span>내가 등록한 오류 제보와 처리 현황을 확인할 수 있습니다.</span></div></header>
    <div className="report-filter-row" aria-label="처리 상태 필터">{filters.map(([value, label]) => <button type="button" key={value} className={filter === value ? "selected" : ""} onClick={() => setFilter(value)}>{label}</button>)}<small>총 {state.items.length}건</small></div>
    {state.loading ? <p className="board-state" role="status">오류 제보를 불러오고 있어요.</p> : state.error ? <div className="board-state board-error" role="alert"><p>{state.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button></div> : filteredItems.length ? <div className="report-list">{filteredItems.map((item) => <button type="button" className="report-list-item" key={item.id} onClick={() => openDetail(item)}><div><span className="report-category">{categoryLabels[item.category] || item.category}</span><strong>{item.question_preview}</strong><small>{item.content_preview || "선택 문구 및 추가 설명 보기"}</small></div><div className="report-list-meta"><span className={`report-status status-${statusKey(item.status)}`}>{statusLabels[item.status] || item.status}</span><time dateTime={item.created_at}>{dateLabel(item.created_at)}</time><b aria-hidden="true">›</b></div></button>)}</div> : <div className="report-empty"><b>등록한 오류 제보가 없습니다.</b><p>답변에서 개선할 점을 발견하면 답변 오류 제보를 남겨 주세요.</p></div>}
  </div></section>;
}
