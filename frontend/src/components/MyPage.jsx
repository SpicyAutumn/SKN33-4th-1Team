import { useEffect, useState } from "react";
import ErrorReportBoard from "./ErrorReportBoard";
import SearchHistory from "./SearchHistory";
import "./MyPage.css";

const sections = [
  ["profile", "내 정보", "이름과 이메일을 관리합니다."],
  ["security", "비밀번호 수정 / 회원 탈퇴", "로그인 보안과 계정을 관리합니다."],
  ["searches", "검색기록", "내 검색기록을 다시 확인합니다."],
  ["reports", "오류 제보", "오류 제보 게시판과 처리 현황을 확인합니다."],
];

function ProfileForm({ api, user, onUpdated }) {
  const [name, setName] = useState(user.name || "");
  const [email, setEmail] = useState(user.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [state, setState] = useState({ busy: false, error: "", message: "" });
  useEffect(() => { setName(user.name || ""); setEmail(user.email || ""); }, [user]);
  const emailChanged = email.trim().toLowerCase() !== (user.email || "").toLowerCase();
  const submit = async (event) => {
    event.preventDefault();
    setState({ busy: true, error: "", message: "" });
    try {
      const updated = await api("me", { method: "PATCH", body: JSON.stringify({ name, email, ...(emailChanged ? { current_password: currentPassword } : {}) }) });
      setCurrentPassword(""); onUpdated(updated);
      setState({ busy: false, error: "", message: "내 정보를 저장했습니다." });
    } catch (error) { setState({ busy: false, error: error.message, message: "" }); }
  };
  return <form className="mypage-form" onSubmit={submit}>
    <label>이름<input value={name} maxLength="50" onChange={(event) => setName(event.target.value)} required /></label>
    <label>이메일<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
    {emailChanged && <label>현재 비밀번호 <small>이메일 변경을 확인합니다.</small><input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>}
    {state.error && <p className="mypage-error" role="alert">{state.error}</p>}
    {state.message && <p className="mypage-success" role="status">{state.message}</p>}
    <button className="primary" disabled={state.busy}>{state.busy ? "저장 중…" : "내 정보 저장"}</button>
  </form>;
}

function SecurityPanel({ api, onDeleted }) {
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [passwordState, setPasswordState] = useState({ busy: false, error: "", message: "" });
  const [deleteState, setDeleteState] = useState({ current: "", confirmation: "", busy: false, error: "" });
  const changePassword = async (event) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) return setPasswordState({ busy: false, error: "새 비밀번호 확인이 일치하지 않습니다.", message: "" });
    setPasswordState({ busy: true, error: "", message: "" });
    try {
      const result = await api("me/password", { method: "POST", body: JSON.stringify({ current_password: passwords.current, new_password: passwords.next }) });
      setPasswords({ current: "", next: "", confirm: "" });
      setPasswordState({ busy: false, error: "", message: result.message || "비밀번호를 변경했습니다." });
    } catch (error) { setPasswordState({ busy: false, error: error.message, message: "" }); }
  };
  const deleteAccount = async (event) => {
    event.preventDefault();
    if (!window.confirm("계정과 내 검색 기록, 오류 제보가 모두 삭제됩니다. 계속할까요?")) return;
    setDeleteState((current) => ({ ...current, busy: true, error: "" }));
    try {
      await api("me", { method: "DELETE", body: JSON.stringify({ current_password: deleteState.current, confirmation: deleteState.confirmation }) });
      onDeleted();
    } catch (error) { setDeleteState((current) => ({ ...current, busy: false, error: error.message })); }
  };
  return <div className="mypage-security">
    <form className="mypage-form" onSubmit={changePassword}><h2>비밀번호 수정</h2><p>현재 비밀번호를 확인한 뒤 새 비밀번호로 바꿉니다. 다른 기기의 로그인은 해제됩니다.</p>
      <label>현재 비밀번호<input type="password" autoComplete="current-password" value={passwords.current} onChange={(event) => setPasswords((current) => ({ ...current, current: event.target.value }))} required /></label>
      <label>새 비밀번호 <small>8자 이상</small><input type="password" autoComplete="new-password" minLength="8" value={passwords.next} onChange={(event) => setPasswords((current) => ({ ...current, next: event.target.value }))} required /></label>
      <label>새 비밀번호 확인<input type="password" autoComplete="new-password" minLength="8" value={passwords.confirm} onChange={(event) => setPasswords((current) => ({ ...current, confirm: event.target.value }))} required /></label>
      {passwordState.error && <p className="mypage-error" role="alert">{passwordState.error}</p>}{passwordState.message && <p className="mypage-success" role="status">{passwordState.message}</p>}
      <button className="primary" disabled={passwordState.busy}>{passwordState.busy ? "변경 중…" : "비밀번호 변경"}</button>
    </form>
    <form className="mypage-delete" onSubmit={deleteAccount}><h2>회원 탈퇴</h2><p>탈퇴하면 계정, 검색기록, 오류 제보가 모두 삭제되며 되돌릴 수 없습니다.</p>
      <label>현재 비밀번호<input type="password" autoComplete="current-password" value={deleteState.current} onChange={(event) => setDeleteState((current) => ({ ...current, current: event.target.value }))} required /></label>
      <label><b>탈퇴 확인</b> <small>아래에 <b>탈퇴</b>라고 정확히 입력해 주세요.</small><input value={deleteState.confirmation} onChange={(event) => setDeleteState((current) => ({ ...current, confirmation: event.target.value }))} placeholder="탈퇴" required /></label>
      {deleteState.error && <p className="mypage-error" role="alert">{deleteState.error}</p>}
      <button className="danger" disabled={deleteState.busy}>{deleteState.busy ? "처리 중…" : "회원 탈퇴"}</button>
    </form>
  </div>;
}

export default function MyPage({ api, user, activeSection = "profile", onNavigate, reportDetailId, onOpenReport, onCloseReport, historyProps, onBack, onUpdated, onDeleted }) {
  const active = sections.some(([value]) => value === activeSection) ? activeSection : "profile";
  const section = sections.find(([value]) => value === active) || sections[0];
  const showSectionHeader = ["profile", "security"].includes(active);
  return <section className="mypage-page"><div className="mypage-shell">
    <button type="button" className="mypage-back" onClick={onBack}>← 홈으로</button>
    <header className="mypage-heading"><p>마이페이지</p><h1>{user.name}님의 마이페이지</h1><span>내 계정과 서비스 이용 기록을 한곳에서 관리하세요.</span></header>
    <div className="mypage-layout"><nav className="mypage-nav" aria-label="마이페이지 메뉴">{sections.map(([value, label]) => <button type="button" key={value} className={active === value ? "selected" : ""} onClick={() => onNavigate(value)}>{label}</button>)}</nav>
      <section className="mypage-content">{showSectionHeader && <header><p>{section[1]}</p><h2>{active === "profile" ? "내 정보" : "계정 관리"}</h2><span>{section[2]}</span></header>}
        {active === "profile" && <ProfileForm api={api} user={user} onUpdated={onUpdated} />}
        {active === "security" && <SecurityPanel api={api} onDeleted={onDeleted} />}
        {active === "searches" && <div className="mypage-embedded"><SearchHistory {...historyProps} expanded /></div>}
        {active === "reports" && <div className="mypage-embedded"><ErrorReportBoard api={api} onBack={() => onNavigate("profile")} selectedId={reportDetailId} onOpenDetail={onOpenReport} onCloseDetail={onCloseReport} /></div>}
      </section>
    </div>
  </div></section>;
}
