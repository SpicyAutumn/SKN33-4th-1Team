import { useEffect, useRef, useState } from "react";

const levels = [["easy", "초등학생"], ["general", "중·고등학생"], ["advanced", "성인 일반"]];
const heritageStories = [
  { title: "경복궁 근정전", subtitle: "조선의 정치 중심지", question: "경복궁 근정전은 어떤 곳인가요?", image: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Gyeongbokgung-GeunJeongJeon.jpg/1280px-Gyeongbokgung-GeunJeongJeon.jpg", imageAlt: "경복궁 근정전" },
  { title: "첨성대", subtitle: "신라의 천문 관측소", question: "첨성대는 어떻게 천문을 관측했나요?", image: "https://upload.wikimedia.org/wikipedia/commons/8/8f/Cheomseongdae_%EC%B2%A8%EC%84%B1%EB%8C%80.jpg", imageAlt: "경주 첨성대" },
  { title: "석굴암", subtitle: "통일신라의 불교 미술", question: "석굴암의 특징을 알려줘", image: "https://commons.wikimedia.org/wiki/Special:FilePath/Korea-Gyeongju-Seokguram%20grotto-Outside%20view-01.jpg?width=1280", imageAlt: "경주 석굴암" },
  { title: "창덕궁 인정전", subtitle: "왕실 의례가 열린 정전", question: "창덕궁 인정전은 어떤 곳인가요?", image: "https://commons.wikimedia.org/wiki/Special:FilePath/Changdeokgung-Injeongjeon.jpg?width=1280", imageAlt: "창덕궁 인정전" },
  { title: "불국사 다보탑", subtitle: "통일신라 석탑의 아름다움", question: "불국사 다보탑의 특징을 알려줘", image: "https://commons.wikimedia.org/wiki/Special:FilePath/Bulguksa_3.jpg?width=1280", imageAlt: "불국사 다보탑" },
  { title: "종묘 정전", subtitle: "조선 왕실 제례의 공간", question: "종묘 정전은 어떤 곳인가요?", image: "https://www.heritage.go.kr/gung/gogung5/images/img_jongmyo_story_bg_19_00.jpg", imageAlt: "종묘 정전" },
  { title: "수원 화성", subtitle: "정조가 세운 과학적 성곽", question: "수원 화성은 왜 지어졌나요?", image: "https://commons.wikimedia.org/wiki/Special:FilePath/Wall_of_Hwaseong_Fortress_in_Suwon%2C_South_Korea.jpg?width=1280", imageAlt: "수원 화성" },
];
const topics = ["조선 왕조", "불교 문화재", "유네스코 세계유산", "고려 청자", "한양 도성", "3·1 운동", "한글 창제", "왕릉과 능침"];
const loadingHeritages = [
  { region: "서울특별시", name: "경복궁", description: "궁궐의 건축과 조선의 역사를 만나는 공간", x: 260, y: 96, symbol: "宮" },
  { region: "경기도 · 수원", name: "수원 화성", description: "도시를 둘러싼 성곽과 성문의 풍경", x: 266, y: 116, symbol: "城" },
  { region: "경상북도 · 경주", name: "첨성대", description: "신라의 천문 관측과 관련된 문화유산", x: 325, y: 190, symbol: "星" },
  { region: "제주특별자치도", name: "성산일출봉", description: "화산 활동이 남긴 자연유산의 풍경", x: 254, y: 286, symbol: "山" },
];

const koreanDate = () => {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = Object.fromEntries(parts.filter(({ type }) => type !== "literal").map(({ type, value: part }) => [type, part]));
  return { key: `${value.year}-${value.month}-${value.day}`, label: `${value.year}년 ${Number(value.month)}월 ${Number(value.day)}일` };
};

const selectDailyStories = (dateKey) => {
  let seed = [...dateKey].reduce((total, character) => ((total * 31) + character.charCodeAt(0)) >>> 0, 2166136261);
  const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const selected = [...heritageStories];
  for (let index = selected.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [selected[index], selected[swapIndex]] = [selected[swapIndex], selected[index]];
  }
  return selected.slice(0, 3);
};

const relativeTime = (value) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "방금 전";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 전`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}일 전`;
  return new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric" }).format(new Date(value));
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

const networkColors = ["#d3a84b", "#3b9a7a", "#4d91ad", "#c9774f", "#8b70b5"];
const shortLabel = (value, limit = 12) => value.length > limit ? `${value.slice(0, limit)}…` : value;

function HeritageNetwork({ initialDocumentId, initialTitle, onAsk }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [trail, setTrail] = useState([]);

  useEffect(() => { setOpen(false); setData(null); setError(""); setTrail([]); }, [initialDocumentId]);

  const load = async (documentId, remember = true) => {
    if (!documentId) return;
    setOpen(true); setLoading(true); setError("");
    try {
      const next = await api(`heritage-network?document_id=${encodeURIComponent(documentId)}`);
      if (remember && data?.root) setTrail((items) => [...items.slice(-4), data.root]);
      setData(next);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const goBack = () => {
    const previous = trail[trail.length - 1];
    if (!previous) return;
    setTrail((items) => items.slice(0, -1));
    void load(previous.document_id, false);
  };

  if (!initialDocumentId) return null;
  if (!open) return <section className="network-entry"><div><b>연관 문화유산 탐색</b><p>답변에 사용된 출처에서 시대·종류·지역으로 이어지는 유산을 살펴보세요.</p></div><button type="button" onClick={() => load(initialDocumentId, false)}>네트워크 열기 →</button></section>;

  const branches = data?.branches || [];
  const centerX = 500; const centerY = 360;
  return <section className="heritage-network">
    <header className="network-header"><div><span>문화유산 네트워크</span><h3>{data?.root?.title || initialTitle}</h3></div><div className="network-actions">{trail.length > 0 && <button type="button" onClick={goBack}>← 이전</button>}<button type="button" onClick={() => setOpen(false)}>접기</button></div></header>
    {loading && <div className="network-status">연결된 문화유산을 찾고 있어요.</div>}
    {error && <div className="network-status network-error">{error}<button type="button" onClick={() => load(data?.root?.document_id || initialDocumentId, false)}>다시 시도</button></div>}
    {data && !loading && !error && <>
      <div className="network-canvas"><svg viewBox="0 0 1000 720" role="img" aria-label={`${data.root.title} 연관 문화유산 네트워크`}>
        {branches.map((branch, branchIndex) => {
          const angle = -Math.PI / 2 + (branchIndex * Math.PI * 2 / Math.max(branches.length, 1));
          const branchX = centerX + Math.cos(angle) * 235;
          const branchY = centerY + Math.sin(angle) * 170;
          const color = networkColors[branchIndex % networkColors.length];
          return <g key={branch.title}>
            <line className="network-edge" x1={centerX} y1={centerY} x2={branchX} y2={branchY} style={{ stroke: color }} />
            <rect className="network-branch" x={branchX - 70} y={branchY - 19} width="140" height="38" rx="19" style={{ stroke: color }} />
            <text className="network-branch-label" x={branchX} y={branchY + 5}>{shortLabel(branch.title, 10)}</text>
            {(branch.nodes || []).map((node, nodeIndex, nodes) => {
              const offset = (nodeIndex - (nodes.length - 1) / 2) * 46;
              const nodeX = centerX + Math.cos(angle) * 385 + (-Math.sin(angle) * offset);
              const nodeY = centerY + Math.sin(angle) * 275 + (Math.cos(angle) * offset);
              return <g key={node.document_id} className="network-node" role="button" tabIndex="0" onClick={() => load(node.document_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") load(node.document_id); }}>
                <title>{`${node.title}\n${node.summary || node.reason}`}</title>
                <line x1={branchX} y1={branchY} x2={nodeX} y2={nodeY} style={{ stroke: color }} />
                <rect x={nodeX - 76} y={nodeY - 18} width="152" height="36" rx="12" style={{ stroke: color }} />
                <text x={nodeX} y={nodeY + 5}>{shortLabel(node.title)}</text>
              </g>;
            })}
          </g>;
        })}
        <g className="network-root"><rect x={centerX - 105} y={centerY - 38} width="210" height="76" rx="22" /><text x={centerX} y={centerY + 7}>{shortLabel(data.root.title, 14)}</text></g>
      </svg></div>
      <div className="network-root-card"><div><b>지금 보고 있는 문화유산</b><p>{data.root.summary || "연결된 문화유산을 선택해 탐색해 보세요."}</p><div>{(data.root.fields || []).map(([label, value]) => <span key={label}><b>{label}</b> {value}</span>)}</div></div><div className="network-root-links"><button type="button" onClick={() => onAsk(`${data.root.title}에 대해 알려줘`)}>이 유산 질문하기</button>{data.root.source_url && <a href={data.root.source_url} target="_blank" rel="noreferrer">공식 원문 ↗</a>}</div></div>
      <div className="network-legend">{branches.map((branch, index) => <span key={branch.title}><i style={{ background: networkColors[index % networkColors.length] }} />{branch.title}</span>)}</div>
    </>}
  </section>;
}

function LoadingJourney({ question, onBack }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const startedAt = Date.now();
    const clock = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(clock);
  }, []);
  useEffect(() => {
    if (paused) return undefined;
    const carousel = window.setInterval(() => setIndex((current) => (current + 1) % loadingHeritages.length), 3500);
    return () => window.clearInterval(carousel);
  }, [paused]);
  const item = loadingHeritages[index];
  return <section className="loading-journey" aria-busy="true">
    <div className="journey-heading"><p className="eyebrow">HERITAGE MOMENTS</p><h2>답변을 기다리며, 우리 문화유산 한 바퀴</h2><p>{question}</p></div>
    <div className="heritage-tour">
      <div className="tour-map"><svg viewBox="130 30 250 285" role="img" aria-label={`대한민국 위치 개념도, 현재 소개 지역 ${item.region}`}>
        <path className="map-land" d="M262 54 L291 63 307 84 314 112 330 138 346 159 349 186 337 207 315 223 297 229 284 244 269 243 265 258 250 250 246 235 231 231 233 215 218 214 221 196 232 180 225 167 238 154 234 139 249 129 246 112 255 99 247 85Z" />
        <ellipse className="map-land" cx="244" cy="287" rx="23" ry="8" />
        {loadingHeritages.map((heritage, heritageIndex) => <circle key={heritage.name} cx={heritage.x} cy={heritage.y} r={heritageIndex === index ? 8 : 4} className={`tour-dot ${heritageIndex === index ? "active" : ""}`} />)}
        <text x="145" y="173">서해</text><text x="345" y="135">동해</text>
      </svg><p>대한민국 · 지역 위치 개념도</p></div>
      <article className="tour-card" key={item.name}><div className="tour-art" aria-hidden="true"><span>{item.symbol}</span></div><div className="tour-copy"><small>기다리는 동안 만나는 문화유산 · {item.region}</small><h3>{item.name}</h3><p>{item.description}</p></div><div className="tour-controls"><span>{index + 1} / {loadingHeritages.length}</span><div><button type="button" onClick={() => setPaused((value) => !value)}>{paused ? "자동 넘김 재개" : "자동 넘김 멈춤"}</button><button type="button" onClick={() => setIndex((index + 1) % loadingHeritages.length)}>다음</button></div></div></article>
    </div>
    <div className="journey-status"><span className="loading-dot" aria-hidden="true" /><div><b>자료를 찾고 답변을 준비하고 있어요.</b><p>위 소개는 검색 결과와 무관하며, 답변의 근거나 실제 검색 위치를 뜻하지 않습니다. · 대기 {elapsed}초</p></div><button type="button" onClick={onBack}>취소</button></div>
  </section>;
}

function SourcePanel({ citations }) {
  return <aside className="sources-panel"><header><div><h2>참고한 자료 <span>{citations.length}</span></h2><p>답변과 자료의 내용을 함께 확인해 보세요.</p></div></header>
    {citations.length ? citations.map((citation, index) => <article className="source-card" key={citation.chunk_id || citation.source_url || index}><b>{String(index + 1).padStart(2, "0")} · {citation.title}</b><small>문화유산 설명 자료</small><details><summary>근거 내용 펼치기</summary><p>{citation.content}</p></details>{citation.source_url && <a href={citation.source_url} target="_blank" rel="noreferrer">원문 보기 ↗</a>}</article>) : <p className="no-sources">표시할 참고 자료가 없습니다.</p>}
  </aside>;
}

function AnswerView({ question, level, result, loading, onBack, onChangeLevel, onReport, onAsk }) {
  const levelLabel = levels.find(([value]) => value === level)?.[1] || "중·고등학생";
  const citations = result?.citations || [];
  const rootCitation = citations.find((citation) => citation.document_id);
  return <section className="answer-page"><div className="answer-shell">
    <button type="button" className="back-to-search" onClick={onBack}>← 첫 화면으로</button>
    <section className="asked-question"><div><span className="question-kicker">질문</span><h1>{question}</h1></div><div className="answer-levels" aria-label={`선택된 설명 수준: ${levelLabel}`}>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => onChangeLevel(value)} disabled={loading || value === level}>{label}</button>)}</div></section>
    {loading && <LoadingJourney question={question} onBack={onBack} />}
    {result?.error && <div className="answer-error">{result.error}</div>}
    {result && !result.error && <>
      <div className="answer-layout"><article className="ai-answer-card">
        <header className="ai-answer-header"><div><span className="ai-mark">AI</span><b>문화유산 AI 답변</b><em>{levelLabel}</em></div></header>
        <div className="ai-answer-body"><section className="core-summary"><b>핵심 요약</b><p>{result.summary || result.message}</p></section><p className="full-answer">{result.message}</p>
          {result.response_type === "needs_clarification" && result.clarification && <section className="clarification-card"><b>질문을 조금 더 구체적으로 알려주세요</b><p>{result.clarification.question || result.message}</p><div>{(result.clarification.options || []).map((option) => <button type="button" key={option.id || option.label} onClick={() => onAsk(`${question} (${option.label})`)}>{option.label}</button>)}</div></section>}
          <p className="answer-note">AI가 생성한 답변입니다. 중요한 정보는 오른쪽 참고 자료의 원문과 함께 확인해 주세요.</p>
          {result.search_record_id && <button type="button" className="report-button" onClick={onReport}>이 답변 오류 제보</button>}
        </div>
      </article><SourcePanel citations={citations} /></div>
      <HeritageNetwork initialDocumentId={rootCitation?.document_id} initialTitle={rootCitation?.title} onAsk={onAsk} />
    </>}
  </div></section>;
}

export default function App() {
  const requestController = useRef(null);
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState(null);
  const [identity, setIdentity] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [reportOpen, setReportOpen] = useState(false);
  const [reportCategory, setReportCategory] = useState("incorrect_fact");
  const [reportContent, setReportContent] = useState("");
  const [reportError, setReportError] = useState("");
  const [question, setQuestion] = useState("");
  const [level, setLevel] = useState("general");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);
  const [today, setToday] = useState(koreanDate);
  const showingAnswer = loading || result;

  useEffect(() => { api("auth/csrf").then(() => api("auth/me")).then(setUser).catch(() => {}); }, []);
  useEffect(() => {
    if (!user) { setRecentSearches([]); return; }
    api("me/searches?limit=5").then(({ items }) => setRecentSearches(items)).catch(() => setRecentSearches([]));
  }, [user]);
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
      const data = authMode === "signup" ? await api("auth/signup", { method: "POST", body: JSON.stringify({ name: username, email: identity, password }) }) : await api("auth/login", { method: "POST", body: JSON.stringify({ email: identity, password }) });
      setUser(data); setAuthMode(null); setIdentity(""); setUsername(""); setPassword("");
    } catch (error) { setAuthError(error.message); }
  };
  const askQuestion = async (nextQuestion, nextLevel = level) => {
    const askedQuestion = nextQuestion.trim();
    if (!askedQuestion) return;
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setQuestion(askedQuestion); setLevel(nextLevel); setLoading(true); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const answer = await api("searches", { method: "POST", body: JSON.stringify({ question: askedQuestion, audience_level: nextLevel }), signal: controller.signal });
      if (requestController.current !== controller) return;
      setResult(answer);
      if (user) api("me/searches?limit=5").then(({ items }) => setRecentSearches(items)).catch(() => {});
    }
    catch (error) { if (!controller.signal.aborted && requestController.current === controller) setResult({ error: error.message }); }
    finally { if (requestController.current === controller) { requestController.current = null; setLoading(false); } }
  };
  const ask = async (event) => { event.preventDefault(); await askQuestion(question); };
  const useQuestion = (nextQuestion, nextLevel = level) => { void askQuestion(nextQuestion, nextLevel); };
  const backToSearch = () => { requestController.current?.abort(); requestController.current = null; setLoading(false); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const logout = async () => { await api("auth/logout", { method: "POST" }); setUser(null); };
  const submitReport = async (event) => {
    event.preventDefault(); setReportError("");
    try { await api("me/error-reports", { method: "POST", body: JSON.stringify({ search_record_id: result.search_record_id, category: reportCategory, content: reportContent }) }); setReportOpen(false); setReportContent(""); }
    catch (error) { setReportError(error.message); }
  };

  return <main>
    <header className="site-header"><a className="brand" href="#top" onClick={backToSearch}><span className="brand-mark" aria-hidden="true">文</span><span>문화유산 AI 가이드</span></a><nav className="site-nav" aria-label="주 메뉴"><a href="#recent-searches" onClick={() => { if (showingAnswer) backToSearch(); }}>내 검색 기록</a><span className="reserved">나의 제보 · 준비 중</span>{user ? <div className="user"><span className="avatar" aria-hidden="true">{user.name?.slice(0, 1)}</span><b>{user.name}님</b><button className="outline" onClick={logout}>로그아웃</button></div> : <button className="outline login-button" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}</nav></header>
    {showingAnswer ? <AnswerView question={question} level={level} result={result} loading={loading} onBack={backToSearch} onChangeLevel={(nextLevel) => askQuestion(question, nextLevel)} onReport={() => { setReportError(""); setReportOpen(true); }} onAsk={(nextQuestion) => askQuestion(nextQuestion, level)} /> : <>
      <section className="home-page" id="top"><div className="home-layout"><section className="search-area"><p className="eyebrow">EXPLORE OUR HERITAGE</p><h1>궁금했던 문화유산,<br />질문에서 시작해 보세요.</h1><p className="hero-copy">나에게 맞는 설명과 함께 참고 자료를 살펴보세요.</p><form onSubmit={ask} className="question-box"><label className="question-row" htmlFor="question"><span aria-hidden="true">⌕</span><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="예: 경복궁은 왜 지어졌나요?" aria-label="문화유산 질문" maxLength="500" /><button className="primary">질문하기</button></label><div className="level-row"><span>설명 수준</span><div>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => setLevel(value)}>{label}</button>)}</div></div></form><p className="search-hint">AI 답변과 함께 사용한 참고 자료를 확인할 수 있습니다.</p><div className="examples"><h3>이런 질문은 어떠세요?</h3><div>{["경복궁 근정전은 어떤 곳인가요?", "고려청자의 특징은 무엇인가요?"].map((example) => <button type="button" key={example} onClick={() => useQuestion(example)}>{example}</button>)}</div></div></section>
        <aside className="history-panel" id="recent-searches" aria-label="최근 검색"><div className="section-title"><div><h2>최근 검색</h2><p>{user ? `${user.name}님의 저장된 질문` : "로그인하면 질문이 저장돼요"}</p></div>{user && <small>{recentSearches.length}건</small>}</div>{user ? recentSearches.length > 0 ? <div className="history-list">{recentSearches.map((item) => <button key={item.id} onClick={() => useQuestion(item.question, item.audience_level)}><span>{item.question}</span><small><em>{levels.find(([value]) => value === item.audience_level)?.[1] || "중·고등학생"}</em>{relativeTime(item.created_at)}</small></button>)}</div> : <p className="empty-history">아직 검색 기록이 없습니다. 첫 질문을 남겨 보세요.</p> : <div className="history-login"><p>이전에 살펴본 답변을 다시 열고 설명 수준도 그대로 이어갈 수 있어요.</p><button type="button" onClick={() => setAuthMode("login")}>로그인하기</button></div>}</aside>
      </div><section className="stories-section"><div className="section-title"><div><h2>오늘의 문화유산 추천</h2><p>{today.label} · 무엇을 물어볼지 고민된다면 여기서 시작해 보세요.</p></div><button type="button" className="more" onClick={() => useQuestion("오늘의 문화유산을 소개해 줘")}>더 보기 →</button></div><div className="story-grid">{selectDailyStories(today.key).map((story) => <button key={story.title} className="story-card" onClick={() => useQuestion(story.question)}><img className="story-image" src={story.image} alt={story.imageAlt} /><span className="story-copy"><b>{story.title}</b><small>{story.subtitle}</small></span></button>)}</div></section></section>
      <section className="topics-section"><div className="section-shell"><h2>추천 주제</h2><div className="topic-list">{topics.map((topic) => <button key={topic} onClick={() => useQuestion(`${topic}에 대해 알려줘`)}>{topic}</button>)}</div></div></section>
    </>}
    <footer><div className="footer-inner"><div><b>문화유산 AI 가이드</b><p>국가 문화유산 정보를 AI로 쉽게 알아보는 공공 서비스</p></div><nav><a href="#top">이용약관</a><a href="#top">개인정보 처리방침</a><a href="#top">오류 제보</a></nav></div></footer>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="이름" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일" type="email" value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
    {reportOpen && <div className="modal"><form onSubmit={submitReport}><button type="button" className="close" onClick={() => setReportOpen(false)}>×</button><h2>답변 오류 제보</h2><select value={reportCategory} onChange={(event) => setReportCategory(event.target.value)}><option value="incorrect_fact">사실이 틀림</option><option value="citation_mismatch">출처가 맞지 않음</option><option value="incomplete_answer">설명이 부족함</option><option value="inappropriate_content">부적절한 내용</option><option value="other">기타</option></select><textarea placeholder="10자 이상으로 내용을 작성해 주세요." value={reportContent} onChange={(event) => setReportContent(event.target.value)} minLength="10" maxLength="2000" required />{reportError && <p className="error">{reportError}</p>}<button className="primary">제보 보내기</button></form></div>}
  </main>;
}
