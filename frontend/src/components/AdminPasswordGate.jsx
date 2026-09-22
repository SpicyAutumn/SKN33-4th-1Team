import { useState } from "react";
import "./AdminPasswordGate.css";

export default function AdminPasswordGate({ api, checking, initialError, onSuccess }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    if (submitting || !password) return;
    setSubmitting(true); setError("");
    try {
      await api("admin/login", { method: "POST", body: JSON.stringify({ password }) });
      setPassword(""); onSuccess();
    } catch (requestError) { setError(requestError.message); }
    finally { setSubmitting(false); }
  };

  return <section className="admin-password-page"><form className="admin-password-card" onSubmit={submit}>
    <p>운영 화면</p><h1>관리자 비밀번호</h1><span>서비스 운영 기록을 확인하려면 관리자 비밀번호를 입력해 주세요.</span>
    {checking ? <div className="admin-password-loading" role="status">접근 상태를 확인하고 있어요.</div> : <><label htmlFor="admin-dashboard-password">비밀번호</label><input id="admin-dashboard-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="관리자 비밀번호 입력" required autoFocus disabled={Boolean(initialError)} />{(initialError || error) && <p className="admin-password-error" role="alert">{initialError || error}</p>}<button className="primary" disabled={submitting || Boolean(initialError)}>{submitting ? "확인 중…" : "관리자 화면 열기"}</button></>}
  </form></section>;
}
