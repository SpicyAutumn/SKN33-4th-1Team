import { useEffect, useRef, useState } from "react";
import { pushPath, readSearchRoute } from "./searchRoutes";
import ShareResult from "./components/ShareResult";
import AnswerContent from "./components/AnswerContent.jsx";
import ErrorReportPanel from "./components/ErrorReportPanel";
import HeritageLoading from "./components/HeritageLoading";
import AnswerMediaLayout from "./components/AnswerMediaLayout";
import HomeLayout from "./components/HomeLayout";
import SearchHistory from "./components/SearchHistory";
import EvidenceSources from "./components/EvidenceSources";
import HeritageNetwork from "./components/HeritageNetwork";
import QuestionRetry from "./components/QuestionRetry";
import ErrorReportBoard from "./components/ErrorReportBoard";
import AdminErrorReportBoard from "./components/AdminErrorReportBoard";
import AdminDashboard from "./components/AdminDashboard";
import AdminUserLog from "./components/AdminUserLog";
import AdminPasswordGate from "./components/AdminPasswordGate";
import AdminSearchLog from "./components/AdminSearchLog";
import LegalDocuments from "./components/LegalDocuments";
import MyPage from "./components/MyPage";
import { levelChangeRequest } from "./clarificationFollowup";

const levels = [["easy", "초등학생"], ["general", "중·고등학생"], ["advanced", "성인 일반"]];
const adminRoute = () => {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (/^\/admin\/searches\/[^/]+$/.test(path)) return "searches";
  if (path === "/admin") return "dashboard";
  if (path === "/admin/users") return "users";
  if (path === "/admin/searches") return "searches";
  if (path === "/admin/reports") return "reports";
  return null;
};
const adminSearchDetailRoute = () => (window.location.pathname.replace(/\/+$/, "") || "/").match(/^\/admin\/searches\/([^/]+)$/)?.[1] || null;
const myPageRoute = () => {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const detail = path.match(/^\/mypage\/(searches|reports)\/([^/]+)$/);
  if (detail) return { section: detail[1], detail: { kind: detail[1] === "searches" ? "search" : "report", id: detail[2] } };
  if (path === "/mypage") return { section: "profile", detail: null };
  if (path === "/mypage/security") return { section: "security", detail: null };
  if (path === "/mypage/searches") return { section: "searches", detail: null };
  if (path === "/mypage/reports") return { section: "reports", detail: null };
  return null;
};
const myPagePath = (section, detailId = null) => detailId ? `/mypage/${section}/${encodeURIComponent(detailId)}` : ({
  profile: "/mypage", security: "/mypage/security", searches: "/mypage/searches", reports: "/mypage/reports",
}[section] || "/mypage");
const koreanDate = () => {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = Object.fromEntries(parts.filter(({ type }) => type !== "literal").map(({ type, value: part }) => [type, part]));
  return { key: `${value.year}-${value.month}-${value.day}`, label: `${value.year}년 ${Number(value.month)}월 ${Number(value.day)}일` };
};

const csrfToken = () => document.cookie.split("; ").find((item) => item.startsWith("csrftoken="))?.split("=")[1];
const ensureCsrfToken = async () => {
  if (csrfToken()) return csrfToken();
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  if (!response.ok) throw new Error("보안 토큰을 준비하지 못했습니다. 페이지를 새로고침해 주세요.");
  const token = csrfToken();
  if (!token) throw new Error("보안 토큰이 설정되지 않았습니다. 페이지를 새로고침해 주세요.");
  return token;
};
const api = async (path, options = {}) => {
  const method = options.method || "GET";
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRFToken"] = await ensureCsrfToken();
  const response = await fetch(`/api/v1/${path}`, { credentials: "include", headers, ...options });
  const rawBody = response.status === 204 ? "" : await response.text();
  let body = {};
  if (rawBody) {
    try { body = JSON.parse(rawBody); }
    catch { throw new Error(`서버 응답 형식 오류(HTTP ${response.status})입니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.`); }
  }
  if (!response.ok) throw new Error(body.error?.message || `요청을 처리하지 못했습니다. (HTTP ${response.status})`);
  return body;
};

export function AnswerView({ question, level, result, loading, loadingRecord, onBack, backLabel = "검색으로 돌아가기", onChangeLevel, onSubmitReport, reportMode = "legacy", capturePreview = false, loadingPreview = null, onAsk, readOnly = false, request }) {
  const [reportActive, setReportActive] = useState(false);
  const answerText = useRef(null);
  const levelLabel = levels.find(([value]) => value === level)?.[1] || "중·고등학생";
  const citations = result?.citations || [];
  const isShareableAnswer = ["answered", "corrected_premise"].includes(result?.response_type);
  return <section className={reportActive ? "answer-page report-active" : "answer-page"}><div className="answer-shell">
    <button type="button" className="back-to-search" onClick={onBack}>← {backLabel}</button>
    <section className="asked-question"><div><span className="question-kicker">⌕ 질문</span><h1>{question}</h1></div><div className="answer-levels" aria-label={`선택된 설명 수준: ${levelLabel}`}>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => onChangeLevel(value)} disabled={readOnly || loading || value === level}>{label}</button>)}</div></section>
    {result?.savedRecord && <p className="saved-answer-note">저장된 답변입니다.{!readOnly && " 설명 수준을 변경하면 새 답변을 생성합니다."}</p>}
    {loading && (loadingRecord ? <div className="answer-loading" role="status">저장된 답변을 불러오고 있어요.</div> : (loadingPreview || <HeritageLoading />))}
    {result?.error && <div className="answer-error" role="alert">{result.error}</div>}
    {result && !result.error && <article className="ai-answer-card">
      <header className="ai-answer-header"><div><span className="ai-mark">AI</span><b>AI 답변</b><em>{levelLabel} 수준</em></div>{!readOnly && !loading && isShareableAnswer && request && (result.search_result_id || result.share_path) && <ShareResult key={result.search_result_id || result.share_path} result={result} request={request} />}</header>
      <div className="ai-answer-body"><AnswerMediaLayout key={result.request_id || result.search_record_id || question + level} media={result.media} citations={citations}><AnswerContent result={result} answerRef={answerText} />
        {onAsk && ["needs_clarification", "insufficient_evidence"].includes(result.response_type) && <QuestionRetry key={result.request_id || result.search_record_id || question + level} question={question} result={result} onAsk={onAsk} busy={loading} />}
        </AnswerMediaLayout>
        <div className={`answer-support${citations.length ? "" : " no-evidence"}`}><EvidenceSources citations={citations} />{result && !result.error && !loading && result.response_type !== "needs_clarification" && <HeritageNetwork answerKey={result.request_id || result.search_record_id || question + level} question={question} citations={result.response_type === "insufficient_evidence" ? [] : citations} recovery={result.response_type === "insufficient_evidence"} onAsk={onAsk} />}</div>
        {result.search_record_id && onSubmitReport && <ErrorReportPanel key={result.search_record_id} recordId={result.search_record_id} answer={result.message} answerRef={answerText} mode={reportMode} capturePreview={capturePreview} onSubmit={onSubmitReport} onOpenChange={setReportActive} />}
      </div>
    </article>}

  </div></section>;
}

export default function App({ request = api } = {}) {
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState(null);
  const [identity, setIdentity] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [question, setQuestion] = useState("");
  const [level, setLevel] = useState("general");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(readSearchRoute(window.location.pathname)));
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [reportBoardPage, setReportBoardPage] = useState(false);
  const [myPage, setMyPage] = useState(() => myPageRoute()?.section || null);
  const [myPageDetail, setMyPageDetail] = useState(() => myPageRoute()?.detail || null);
  const [returnToMyPage, setReturnToMyPage] = useState(null);
  const [adminPage, setAdminPage] = useState(adminRoute);
  const [adminSearchDetail, setAdminSearchDetail] = useState(adminSearchDetailRoute);
  const [adminSearchRecord, setAdminSearchRecord] = useState({ item: null, loading: false, error: "" });
  const [adminAccess, setAdminAccess] = useState("checking");
  const [adminAccessError, setAdminAccessError] = useState("");
  const [historyVersion, setHistoryVersion] = useState(0);
  const [activeQuestionRequest, setActiveQuestionRequest] = useState(null);
  const requestVersion = useRef(0);
  const historyMenu = useRef(null);
  const [today, setToday] = useState(koreanDate);
  const showingAnswer = loading || result;

  useEffect(() => { request("auth/csrf").then(() => request("auth/me")).then(setUser).catch(() => {}); }, [request]);
  useEffect(() => {
    if (!adminPage) return undefined;
    let active = true;
    setAdminAccess("checking"); setAdminAccessError("");
    request("admin/session").then(({ authenticated }) => {
      if (active) setAdminAccess(authenticated ? "granted" : "denied");
    }).catch((error) => {
      if (active) { setAdminAccess("denied"); setAdminAccessError(error.message); }
    });
    return () => { active = false; };
  }, [adminPage, request]);
  useEffect(() => {
    const restoreLocation = async () => {
      const version = ++requestVersion.current;
      if (window.location.pathname.replace(/\/+$/, "") === "/history") {
        window.history.replaceState({}, "", "/mypage/searches");
      }
      const route = readSearchRoute(window.location.pathname);
      const myRoute = myPageRoute();
      setMyPage(myRoute?.section || null); setMyPageDetail(myRoute?.detail || null);
      setReturnToMyPage(myRoute?.detail?.kind === "search" ? "searches" : null);
      setActiveQuestionRequest(null);
      setAdminPage(adminRoute()); setAdminSearchDetail(adminSearchDetailRoute());
      setReportBoardPage(window.location.pathname === "/reports");
      setResult(null); setQuestion(""); setLoading(Boolean(route)); setLoadingRecord(Boolean(route));
      if (!route) {
        if (window.location.pathname.startsWith("/search/") || window.location.pathname.startsWith("/share/")) {
          setResult({ error: "올바르지 않은 결과 주소입니다. 검색으로 돌아가 다시 검색해 주세요." });
        }
        return;
      }
      try {
        const answer = await request(route.endpoint);
        if (version !== requestVersion.current) return;
        setQuestion(answer.question); setLevel(answer.audience_level);
        setResult({ ...answer, savedRecord: true });
      } catch (error) {
        if (version === requestVersion.current) setResult({ error: error.message });
      } finally {
        if (version === requestVersion.current) { setLoading(false); setLoadingRecord(false); }
      }
    };
    void restoreLocation();
    window.addEventListener("popstate", restoreLocation);
    return () => { ++requestVersion.current; window.removeEventListener("popstate", restoreLocation); };
  }, [request]);
  useEffect(() => {
    const timer = window.setInterval(() => setToday((current) => {
      const next = koreanDate();
      return next.key === current.key ? current : next;
    }), 60000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!user || myPageDetail?.kind !== "search") return undefined;
    setActiveQuestionRequest(null);
    let active = true;
    const version = ++requestVersion.current;
    setLoadingRecord(true); setLoading(true); setResult(null);
    request("me/searches/" + encodeURIComponent(myPageDetail.id)).then((record) => {
      if (!active || version !== requestVersion.current) return;
      setQuestion(record.question); setLevel(record.audience_level);
      setResult({ ...record, search_record_id: record.id, search_result_id: record.id, savedRecord: true });
    }).catch((error) => {
      if (active && version === requestVersion.current) setResult({ error: error.message });
    }).finally(() => {
      if (active && version === requestVersion.current) { setLoading(false); setLoadingRecord(false); }
    });
    return () => { active = false; };
  }, [myPageDetail, request, user]);
  useEffect(() => {
    if (adminPage !== "searches" || !adminSearchDetail || adminAccess !== "granted") { setAdminSearchRecord({ item: null, loading: false, error: "" }); return undefined; }
    let active = true;
    setAdminSearchRecord({ item: null, loading: true, error: "" });
    request("admin/searches/" + encodeURIComponent(adminSearchDetail)).then((item) => {
      if (active) setAdminSearchRecord({ item, loading: false, error: "" });
    }).catch((error) => { if (active) setAdminSearchRecord({ item: null, loading: false, error: error.message }); });
    return () => { active = false; };
  }, [adminAccess, adminPage, adminSearchDetail, request]);

  const submitAuth = async (event) => {
    event.preventDefault(); setAuthError("");
    try {
      const data = authMode === "signup" ? await request("auth/signup", { method: "POST", body: JSON.stringify({ name: username, email: identity, password }) }) : await request("auth/login", { method: "POST", body: JSON.stringify({ email: identity, password }) });
      setUser(data); setAuthMode(null); setIdentity(""); setUsername(""); setPassword("");
      if (readSearchRoute(window.location.pathname)) window.dispatchEvent(new PopStateEvent("popstate"));
    } catch (error) { setAuthError(error.message); }
  };
  const askQuestion = async (nextQuestion, nextLevel = level) => {
    const followup = typeof nextQuestion === "string" ? { question: nextQuestion } : nextQuestion;
    const askedQuestion = String(followup?.question || "").trim();
    if (!askedQuestion) return;
    const version = ++requestVersion.current;
    setReportBoardPage(false); setMyPage(false); setMyPageDetail(null); setReturnToMyPage(false); setAdminPage(null); setAdminSearchDetail(null); setLoadingRecord(false);
    setActiveQuestionRequest(followup);
    setQuestion(askedQuestion); setLevel(nextLevel); setLoading(true); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const answer = await request("searches", { method: "POST", body: JSON.stringify({
        question: askedQuestion,
        audience_level: nextLevel,
        ...(followup?.interaction_id ? { interaction_id: followup.interaction_id } : {}),
        ...(followup?.selected_source_chunk_ids?.length ? { selected_source_chunk_ids: followup.selected_source_chunk_ids } : {}),
        ...(followup?.clarification_context ? { clarification_context: followup.clarification_context } : {}),
      }) });
      if (version !== requestVersion.current) return;
      setResult(answer);
      if (answer.search_result_id) pushPath(`/search/${answer.search_result_id}`);
      setHistoryVersion((value) => value + 1);
    }
    catch (error) { if (version === requestVersion.current) setResult({ error: error.message }); }
    finally { if (version === requestVersion.current) setLoading(false); }
  };
  const ask = async (event) => { event.preventDefault(); await askQuestion(question); };
  const useQuestion = (nextQuestion, nextLevel = level) => { void askQuestion(nextQuestion, nextLevel); };
  const openRecord = (item) => {
    if (historyMenu.current) historyMenu.current.open = false;
    pushPath(myPagePath("searches", item.id));
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openPage = (path) => {
    pushPath(path);
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const historyProps = { api: request, refreshKey: historyVersion, onOpen: openRecord, busy: loading, onMore: () => { if (historyMenu.current) historyMenu.current.open = false; openPage(myPagePath("searches")); } };
  const backToSearch = () => {
    ++requestVersion.current;
    setQuestion("");
    setActiveQuestionRequest(null);
    setLoading(false); setLoadingRecord(false);
    setReportBoardPage(false); setMyPage(false); setMyPageDetail(null); setReturnToMyPage(false); setAdminPage(null); setAdminSearchDetail(null);
    setResult(null);
    pushPath("/");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openAdminPage = (page) => { ++requestVersion.current; setLoading(false); setReportBoardPage(false); setMyPage(false); setMyPageDetail(null); setReturnToMyPage(false); setResult(null); setAdminPage(page); setAdminSearchDetail(null); window.history.pushState({}, "", page === "reports" ? "/admin/reports" : page === "users" ? "/admin/users" : page === "searches" ? "/admin/searches" : "/admin"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const openAdminSearchDetail = (recordId) => { setAdminPage("searches"); setAdminSearchDetail(recordId); window.history.pushState({}, "", `/admin/searches/${encodeURIComponent(recordId)}`); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const closeAdminSearchDetail = () => { setAdminPage("searches"); setAdminSearchDetail(null); window.history.pushState({}, "", "/admin/searches"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const logout = async () => { await request("auth/logout", { method: "POST" }); setUser(null); backToSearch(); };
  const logoutAdmin = async () => { await request("admin/logout", { method: "POST" }); setAdminAccess("denied"); setAdminAccessError(""); };
  const openMyPage = (section = "profile") => { setActiveQuestionRequest(null); ++requestVersion.current; setLoading(false); setLoadingRecord(false); setReportBoardPage(false); setAdminPage(null); setResult(null); setMyPageDetail(null); setReturnToMyPage(null); setMyPage(section); window.history.pushState({}, "", myPagePath(section)); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const openReportDetail = (reportId) => { setMyPage("reports"); setMyPageDetail({ kind: "report", id: reportId }); window.history.pushState({}, "", myPagePath("reports", reportId)); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const closeReportDetail = () => { setMyPage("reports"); setMyPageDetail(null); window.history.pushState({}, "", myPagePath("reports")); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const backToMyPage = () => { ++requestVersion.current; const section = returnToMyPage || "searches"; setQuestion(""); setLoading(false); setLoadingRecord(false); setReportBoardPage(false); setAdminPage(null); setResult(null); setMyPage(section); setMyPageDetail(null); setReturnToMyPage(null); window.history.pushState({}, "", myPagePath(section)); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const afterAccountDeleted = () => { setActiveQuestionRequest(null); setUser(null); setMyPage(false); setMyPageDetail(null); setReturnToMyPage(false); setReportBoardPage(false); setAdminSearchDetail(null); setResult(null); setQuestion(""); window.scrollTo({ top: 0, behavior: "smooth" }); };


  return <main>
    <header className="site-header"><a className="brand" href="/" onClick={(event) => { event.preventDefault(); backToSearch(); }}><span className="brand-mark" aria-hidden="true">📚</span><span>문화유산 AI 가이드</span></a>{adminPage && adminAccess === "granted" ? <button className="outline" onClick={logoutAdmin}>관리자 로그아웃</button> : user ? <div className="user">{showingAnswer && !reportBoardPage && !myPage && !adminPage && <details ref={historyMenu} className="history-menu" onKeyDown={(event) => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary").focus(); } }}><summary>내 검색 기록</summary><SearchHistory key={user.id} {...historyProps} /></details>}<b>{user.name}</b><button type="button" className="user-board-link" onClick={() => openMyPage()}>마이페이지</button><button className="outline" onClick={logout}>로그아웃</button></div> : <button className="outline login-button" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}</header>
    {adminPage && adminAccess !== "granted" ? <AdminPasswordGate api={request} checking={adminAccess === "checking"} initialError={adminAccessError} onSuccess={() => { setAdminAccess("granted"); setAdminAccessError(""); }} /> : adminPage === "dashboard" ? <AdminDashboard api={request} onOpenUsers={() => openAdminPage("users")} onOpenReports={() => openAdminPage("reports")} onOpenSearches={() => openAdminPage("searches")} onOpenSearchDetail={openAdminSearchDetail} /> : adminPage === "users" ? <AdminUserLog api={request} onBack={() => openAdminPage("dashboard")} /> : adminPage === "searches" && adminSearchDetail ? <AnswerView question={adminSearchRecord.item?.question || "검색기록을 불러오는 중입니다."} level={adminSearchRecord.item?.audience_level || "general"} result={adminSearchRecord.error ? { error: adminSearchRecord.error } : adminSearchRecord.item ? { ...adminSearchRecord.item, savedRecord: true } : null} loading={adminSearchRecord.loading} loadingRecord={adminSearchRecord.loading} onBack={closeAdminSearchDetail} backLabel="관리자 검색기록으로 돌아가기" onChangeLevel={() => {}} readOnly /> : adminPage === "searches" ? <AdminSearchLog api={request} onBack={() => openAdminPage("dashboard")} selectedId={null} onOpenDetail={openAdminSearchDetail} onCloseDetail={closeAdminSearchDetail} /> : adminPage === "reports" ? <AdminErrorReportBoard api={request} onBack={() => openAdminPage("dashboard")} /> : myPageDetail?.kind === "search" && user ? <AnswerView request={request} question={question} level={level} result={result} loading={loading} loadingRecord={loadingRecord} onBack={backToMyPage} backLabel="나의 검색기록으로 돌아가기" onChangeLevel={(nextLevel) => askQuestion(levelChangeRequest(activeQuestionRequest, question), nextLevel)} onSubmitReport={user && !result?.shared ? (payload) => request("me/error-reports", { method: "POST", body: JSON.stringify(payload) }) : undefined} onAsk={(nextQuestion) => askQuestion(nextQuestion, level)} /> : myPage && user ? <MyPage api={request} user={user} activeSection={myPage} onNavigate={openMyPage} reportDetailId={myPageDetail?.kind === "report" ? myPageDetail.id : null} onOpenReport={openReportDetail} onCloseReport={closeReportDetail} historyProps={{ ...historyProps, onMore: () => {}, onOpen: openRecord }} onBack={backToSearch} onUpdated={setUser} onDeleted={afterAccountDeleted} /> : reportBoardPage && user ? <ErrorReportBoard api={request} onBack={backToSearch} /> : showingAnswer ? <AnswerView request={request} question={question} level={level} result={result} loading={loading} loadingRecord={loadingRecord} onBack={returnToMyPage ? backToMyPage : backToSearch} backLabel={returnToMyPage ? "마이페이지로 돌아가기" : "검색으로 돌아가기"} onChangeLevel={(nextLevel) => askQuestion(levelChangeRequest(activeQuestionRequest, question), nextLevel)} onSubmitReport={user && !result?.shared ? (payload) => request("me/error-reports", { method: "POST", body: JSON.stringify(payload) }) : undefined} onAsk={(nextQuestion) => askQuestion(nextQuestion, level)} /> : <HomeLayout user={user} historyProps={historyProps} question={question} onQuestionChange={setQuestion} onSubmit={ask} level={level} levels={levels} onLevelChange={setLevel} onAsk={useQuestion} dateLabel={today.label} onLogin={() => setAuthMode("login")} />}
    <footer><div className="footer-inner"><div><b>문화유산 AI 가이드</b><p>문화유산 정보를 AI로 알아보는 교육 프로젝트</p></div><LegalDocuments /></div></footer>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="이름" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일" type="email" value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
  </main>;
}
