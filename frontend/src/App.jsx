import { useEffect, useRef, useState } from "react";
import AnswerContent from "./components/AnswerContent.jsx";
import ErrorReportPanel from "./components/ErrorReportPanel";
import HeritageLoading from "./components/HeritageLoading";
import AnswerMediaLayout from "./components/AnswerMediaLayout";
import HomeLayout from "./components/HomeLayout";
import SearchHistory from "./components/SearchHistory";
import EvidenceSources from "./components/EvidenceSources";
import HeritageNetwork from "./components/HeritageNetwork";
import ErrorReportBoard from "./components/ErrorReportBoard";
import AdminErrorReportBoard from "./components/AdminErrorReportBoard";
import { clarificationFollowup } from "./clarificationFollowup";

const levels = [["easy", "초등학생"], ["general", "중·고등학생"], ["advanced", "성인 일반"]];
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

export function AnswerView({ question, level, result, loading, loadingRecord, onBack, onChangeLevel, onSubmitReport, reportMode = "legacy", capturePreview = false, loadingPreview = null, onAsk }) {
  const [reportActive, setReportActive] = useState(false);
  const answerText = useRef(null);
  const levelLabel = levels.find(([value]) => value === level)?.[1] || "중·고등학생";
  const citations = result?.citations || [];
  return <section className={reportActive ? "answer-page report-active" : "answer-page"}><div className="answer-shell">
    <button type="button" className="back-to-search" onClick={onBack}>← 검색으로 돌아가기</button>
    <section className="asked-question"><div><span className="question-kicker">⌕ 질문</span><h1>{question}</h1></div><div className="answer-levels" aria-label={`선택된 설명 수준: ${levelLabel}`}>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => onChangeLevel(value)} disabled={loading || value === level}>{label}</button>)}</div></section>
    {result?.savedRecord && <p className="saved-answer-note">저장된 답변입니다. 설명 수준을 변경하면 새 답변을 생성합니다.</p>}
    {loading && (loadingRecord ? <div className="answer-loading" role="status">저장된 답변을 불러오고 있어요.</div> : (loadingPreview || <HeritageLoading />))}
    {result?.error && <div className="answer-error" role="alert">{result.error}</div>}
    {result && !result.error && <article className="ai-answer-card">
      <header className="ai-answer-header"><div><span className="ai-mark">AI</span><b>AI 답변</b><em>{levelLabel} 수준</em></div></header>
      <div className="ai-answer-body"><AnswerMediaLayout key={result.request_id || result.search_record_id || question + level} media={result.media} citations={citations}><AnswerContent result={result} answerRef={answerText} />
        {result.response_type === "needs_clarification" && result.clarification && <section className="clarification-card"><b>질문을 조금 더 구체적으로 알려주세요</b><p>{result.clarification.question || result.message}</p><div>{(result.clarification.options || []).map((option) => <button type="button" key={option.id || option.label} onClick={() => onAsk(clarificationFollowup(question, result, option))}>{option.label}</button>)}</div></section>}
        </AnswerMediaLayout>
        <div className={`answer-support${citations.length ? "" : " no-evidence"}`}><EvidenceSources citations={citations} />{result && !result.error && !loading && result.response_type !== "needs_clarification" && <HeritageNetwork answerKey={result.request_id || result.search_record_id || question + level} question={question} citations={citations} />}</div>
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
  const [loading, setLoading] = useState(false);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [historyPage, setHistoryPage] = useState(false);
  const [reportBoardPage, setReportBoardPage] = useState(false);
  const [adminReportPage, setAdminReportPage] = useState(false);
  const [historyVersion, setHistoryVersion] = useState(0);
  const requestVersion = useRef(0);
  const historyMenu = useRef(null);
  const [today, setToday] = useState(koreanDate);
  const showingAnswer = loading || result;

  useEffect(() => { request("auth/csrf").then(() => request("auth/me")).then(setUser).catch(() => {}); }, [request]);
  useEffect(() => {
    const timer = window.setInterval(() => setToday((current) => {
      const next = koreanDate();
      return next.key === current.key ? current : next;
    }), 60000);
    return () => window.clearInterval(timer);
  }, []);

  const submitAuth = async (event) => {
    event.preventDefault(); setAuthError("");
    try {
      const data = authMode === "signup" ? await request("auth/signup", { method: "POST", body: JSON.stringify({ name: username, email: identity, password }) }) : await request("auth/login", { method: "POST", body: JSON.stringify({ email: identity, password }) });
      setUser(data); setAuthMode(null); setIdentity(""); setUsername(""); setPassword("");
    } catch (error) { setAuthError(error.message); }
  };
  const askQuestion = async (nextQuestion, nextLevel = level) => {
    const followup = typeof nextQuestion === "string" ? { question: nextQuestion } : nextQuestion;
    const askedQuestion = String(followup?.question || "").trim();
    if (!askedQuestion) return;
    const version = ++requestVersion.current;
    setHistoryPage(false); setReportBoardPage(false); setAdminReportPage(false); setLoadingRecord(false);
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
      setHistoryVersion((value) => value + 1);
    }
    catch (error) { if (version === requestVersion.current) setResult({ error: error.message }); }
    finally { if (version === requestVersion.current) setLoading(false); }
  };
  const ask = async (event) => { event.preventDefault(); await askQuestion(question); };
  const useQuestion = (nextQuestion, nextLevel = level) => { void askQuestion(nextQuestion, nextLevel); };
  const openRecord = async (item) => {
    if (historyMenu.current) historyMenu.current.open = false;
    const version = ++requestVersion.current;
    setLoadingRecord(true); setHistoryPage(false); setReportBoardPage(false); setAdminReportPage(false); setQuestion(item.question); setLevel(item.audience_level); setLoading(true); setResult(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const record = await request("me/searches/" + encodeURIComponent(item.id));
      if (version !== requestVersion.current) return;
      setQuestion(record.question); setLevel(record.audience_level);
      setResult({ ...record, search_record_id: record.id, savedRecord: true });
    } catch (error) { if (version === requestVersion.current) setResult({ error: error.message }); }
    finally { if (version === requestVersion.current) setLoading(false); }
  };
  const historyProps = { api: request, refreshKey: historyVersion, onOpen: openRecord, busy: loading, onMore: () => { if (historyMenu.current) historyMenu.current.open = false; setHistoryPage(true); } };
  const backToSearch = () => { ++requestVersion.current; setLoading(false); setHistoryPage(false); setReportBoardPage(false); setAdminReportPage(false); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const logout = async () => { await request("auth/logout", { method: "POST" }); setUser(null); backToSearch(); };


  return <main>
    <header className="site-header"><a className="brand" href="#top" onClick={backToSearch}><span className="brand-mark" aria-hidden="true">📚</span><span>문화유산 AI 가이드</span></a>{user ? <div className="user">{showingAnswer && !historyPage && !reportBoardPage && !adminReportPage && <details ref={historyMenu} className="history-menu" onKeyDown={(event) => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary").focus(); } }}><summary>내 검색 기록</summary><SearchHistory key={user.id} {...historyProps} /></details>}<b>{user.name}</b>{user.role !== "admin" && <button type="button" className="user-board-link" onClick={() => { setHistoryPage(false); setAdminReportPage(false); setReportBoardPage(true); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); }}>게시판</button>}{user.role === "admin" && <button type="button" className="user-board-link" onClick={() => { setHistoryPage(false); setReportBoardPage(false); setAdminReportPage(true); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); }}>관리자</button>}<button className="outline" onClick={logout}>로그아웃</button></div> : <button className="outline login-button" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}</header>
    {adminReportPage && user?.role === "admin" ? <AdminErrorReportBoard api={request} onBack={backToSearch} /> : reportBoardPage && user?.role !== "admin" ? <ErrorReportBoard api={request} onBack={backToSearch} /> : historyPage && user ? <div className="history-page"><SearchHistory key={user.id} {...historyProps} expanded onBack={() => setHistoryPage(false)} /></div> : showingAnswer ? <AnswerView question={question} level={level} result={result} loading={loading} loadingRecord={loadingRecord} onBack={backToSearch} onChangeLevel={(nextLevel) => askQuestion(question, nextLevel)} onSubmitReport={(payload) => request("me/error-reports", { method: "POST", body: JSON.stringify(payload) })} onAsk={(nextQuestion) => askQuestion(nextQuestion, level)} /> : <HomeLayout user={user} historyProps={historyProps} question={question} onQuestionChange={setQuestion} onSubmit={ask} level={level} levels={levels} onLevelChange={setLevel} onAsk={useQuestion} dateLabel={today.label} onLogin={() => setAuthMode("login")} />}
    <footer><div className="footer-inner"><div><b>문화유산 AI 가이드</b><p>국가 문화유산 정보를 AI로 쉽게 알아보는 공공 서비스</p></div><nav><a href="#top">이용약관</a><a href="#top">개인정보 처리방침</a><a href="#top">오류 제보</a></nav></div></footer>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="이름" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일" type="email" value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
  </main>;
}
