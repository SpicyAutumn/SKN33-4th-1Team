import { useEffect, useState } from "react";
import "./AdminErrorReportBoard.css";

const categoryLabels = { incorrect_fact: "사실이 틀림", citation_mismatch: "출처가 맞지 않음", incomplete_answer: "설명이 부족함", inappropriate_content: "부적절한 내용", other: "기타" };
const statusLabels = { received: "접수됨", reviewing: "확인 중", completed: "처리 완료" };
const filters = [["all", "전체"], ["received", "접수됨"], ["reviewing", "확인 중"], ["completed", "처리 완료"]];
const dateLabel = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 미제공" : new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
};

export default function AdminErrorReportBoard({ api, onBack }) {
  const [state, setState] = useState({ items: [], loading: true, error: "" });
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState({ item: null, loading: false, error: "" });
  const [status, setStatus] = useState("received");
  const [reply, setReply] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ items: [], loading: true, error: "" });
    api(`admin/error-reports?status=${filter}`).then(({ items }) => { if (active) setState({ items: items || [], loading: false, error: "" }); }).catch((error) => { if (active) setState({ items: [], loading: false, error: error.message }); });
    return () => { active = false; };
  }, [api, filter, retry]);
  const openDetail = async (id) => {
    setSelectedId(id); setDetail({ item: null, loading: true, error: "" }); setSaveMessage("");
    try {
      const item = await api(`admin/error-reports/${encodeURIComponent(id)}`);
      setDetail({ item, loading: false, error: "" }); setStatus(item.status); setReply(item.staff_reply || "");
    } catch (error) { setDetail({ item: null, loading: false, error: error.message }); }
  };
  const save = async (event) => {
    event.preventDefault(); if (!selectedId || saving) return;
    setSaving(true); setSaveMessage("");
    try {
      const item = await api(`admin/error-reports/${encodeURIComponent(selectedId)}`, { method: "PATCH", body: JSON.stringify({ status, staff_reply: reply }) });
      setDetail({ item, loading: false, error: "" }); setSaveMessage("처리 내용이 저장되었습니다.");
      setState((current) => ({ ...current, items: current.items.map((report) => report.id === item.id ? { ...report, status: item.status, updated_at: item.updated_at } : report) }));
    } catch (error) { setSaveMessage(error.message); }
    finally { setSaving(false); }
  };
  const report = detail.item;
  return <section className="admin-report-page"><div className="admin-report-shell">
    <button type="button" className="board-back" onClick={onBack}>← 홈으로</button>
    <header className="admin-report-heading"><div><p>관리자 전용</p><h1>오류 제보 관리</h1><span>접수된 제보를 확인하고 처리 상태와 답변을 등록합니다.</span></div></header>
    <div className="admin-filter-row" aria-label="처리 상태 필터">{filters.map(([value, label]) => <button type="button" key={value} className={filter === value ? "selected" : ""} onClick={() => { setFilter(value); setSelectedId(null); setDetail({ item: null, loading: false, error: "" }); }}>{label}</button>)}<small>총 {state.items.length}건</small></div>
    <div className="admin-workspace">
      <section className="admin-report-list" aria-label="오류 제보 목록">{state.loading ? <p className="admin-state" role="status">제보를 불러오고 있어요.</p> : state.error ? <div className="admin-state admin-error" role="alert"><p>{state.error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button></div> : state.items.length ? state.items.map((item) => <button type="button" key={item.id} className={selectedId === item.id ? "selected" : ""} onClick={() => openDetail(item.id)}><span>{categoryLabels[item.category] || item.category}</span><strong>{item.question_preview}</strong><small>{item.reporter_name} · {dateLabel(item.created_at)}</small><em className={`admin-status status-${item.status}`}>{statusLabels[item.status] || item.status}</em></button>) : <p className="admin-state">처리할 제보가 없습니다.</p>}</section>
      <section className="admin-report-detail" aria-live="polite">{!selectedId ? <div className="admin-detail-empty"><b>왼쪽 목록에서 제보를 선택해 주세요.</b><p>제보 내용과 AI 답변을 확인한 뒤 처리 결과를 등록할 수 있습니다.</p></div> : detail.loading ? <p className="admin-state" role="status">제보 내용을 불러오고 있어요.</p> : detail.error ? <div className="admin-state admin-error" role="alert"><p>{detail.error}</p><button type="button" onClick={() => openDetail(selectedId)}>다시 시도</button></div> : report && <><header><div><span className="report-category">{categoryLabels[report.category] || report.category}</span><h2>{report.question}</h2></div><span className={`admin-status status-${report.status}`}>{statusLabels[report.status] || report.status}</span></header><dl className="admin-reporter"><div><dt>제보자</dt><dd>{report.reporter_name}</dd></div><div><dt>이메일</dt><dd>{report.reporter_email}</dd></div><div><dt>등록일</dt><dd>{dateLabel(report.created_at)}</dd></div></dl><section><h3>제보 내용</h3><p className="admin-report-content">{report.content}</p></section><details className="admin-original-answer"><summary>제보 당시 AI 답변 전문 <span>펼치기</span></summary><p>{report.answer_text}</p></details><form onSubmit={save} className="admin-process-form"><h3>처리 등록</h3><label htmlFor="admin-status">처리 상태</label><select id="admin-status" value={status} disabled={saving} onChange={(event) => setStatus(event.target.value)}><option value="received">접수됨</option><option value="reviewing">확인 중</option><option value="completed">처리 완료</option></select><label htmlFor="admin-reply">담당자 답변</label><textarea id="admin-reply" value={reply} disabled={saving} maxLength="2000" placeholder="사용자에게 전달할 처리 결과를 입력해 주세요." onChange={(event) => setReply(event.target.value)} /><small>처리 완료 시 10자 이상의 담당자 답변이 필요합니다. {reply.length}/2000</small>{saveMessage && <p className={saveMessage === "처리 내용이 저장되었습니다." ? "admin-success" : "admin-save-error"} role="status">{saveMessage}</p>}<button className="primary" disabled={saving}>{saving ? "저장 중…" : "처리 내용 저장"}</button></form></>}</section>
    </div>
  </div></section>;
}
