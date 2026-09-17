import { useEffect, useState } from "react";

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

const summaryFromAnswer = (message = "") => {
  const sentences = message.replace(/\s+/g, " ").trim().match(/[^.!?]+[.!?]?/g) || [];
  return sentences.slice(0, 2).join(" ").trim() || message;
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
const api = async (path, options = {}) => {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (!["GET", "HEAD", "OPTIONS"].includes(options.method || "GET") && csrfToken()) headers["X-CSRFToken"] = csrfToken();
  const response = await fetch(`/api/v1/${path}`, { credentials: "include", headers, ...options });
  const body = response.status === 204 ? {} : await response.json();
  if (!response.ok) throw new Error(body.error?.message || "요청을 처리하지 못했습니다.");
  return body;
};

function AnswerView({ question, level, result, loading, onBack, onChangeLevel, onReport, onAsk }) {
  const levelLabel = levels.find(([value]) => value === level)?.[1] || "중·고등학생";
  const citations = result?.citations || [];
  return <section className="answer-page"><div className="answer-shell">
    <button type="button" className="back-to-search" onClick={onBack}>← 검색으로 돌아가기</button>
    <section className="asked-question"><div><span className="question-kicker">⌕ 질문</span><h1>{question}</h1></div><div className="answer-levels" aria-label={`선택된 설명 수준: ${levelLabel}`}>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => onChangeLevel(value)} disabled={loading || value === level}>{label}</button>)}</div></section>
    {loading && <div className="answer-loading">자료를 찾고 답변을 준비하고 있어요.</div>}
    {result?.error && <div className="answer-error">{result.error}</div>}
    {result && !result.error && <article className="ai-answer-card">
      <header className="ai-answer-header"><div><span className="ai-mark">AI</span><b>AI 답변</b><em>{levelLabel} 수준</em></div></header>
      <div className="ai-answer-body"><section className="core-summary"><b>★ 핵심 요약</b><p>{summaryFromAnswer(result.message)}</p></section><p className="full-answer">{result.message}</p>
        {result.response_type === "needs_clarification" && result.clarification && <section className="clarification-card"><b>질문을 조금 더 구체적으로 알려주세요</b><p>{result.clarification.question || result.message}</p><div>{(result.clarification.options || []).map((option) => <button type="button" key={option.id || option.label} onClick={() => onAsk(`${question} (${option.label})`)}>{option.label}</button>)}</div></section>}
        {citations.length > 0 && <details className="evidence-panel"><summary><span>◌ 근거 확인</span><span className="evidence-chevron">⌄</span></summary><div className="evidence-content">{citations.map((citation) => <article key={citation.chunk_id || citation.source_url}><b>{citation.title}</b><p>{citation.content}</p><a href={citation.source_url} target="_blank" rel="noreferrer">원문 보기 ↗</a></article>)}</div></details>}
        {result.search_record_id && <button type="button" className="report-button" onClick={onReport}>이 답변 오류 제보</button>}
      </div>
    </article>}
  </div></section>;
}

export default function App() {
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
    setQuestion(askedQuestion); setLevel(nextLevel); setLoading(true); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const answer = await api("searches", { method: "POST", body: JSON.stringify({ question: askedQuestion, audience_level: nextLevel }) });
      setResult(answer);
      if (user) api("me/searches?limit=5").then(({ items }) => setRecentSearches(items)).catch(() => {});
    }
    catch (error) { setResult({ error: error.message }); }
    finally { setLoading(false); }
  };
  const ask = async (event) => { event.preventDefault(); await askQuestion(question); };
  const useQuestion = (nextQuestion, nextLevel = level) => { void askQuestion(nextQuestion, nextLevel); };
  const backToSearch = () => { setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const logout = async () => { await api("auth/logout", { method: "POST" }); setUser(null); };
  const submitReport = async (event) => {
    event.preventDefault(); setReportError("");
    try { await api("me/error-reports", { method: "POST", body: JSON.stringify({ search_record_id: result.search_record_id, category: reportCategory, content: reportContent }) }); setReportOpen(false); setReportContent(""); }
    catch (error) { setReportError(error.message); }
  };

  return <main>
    <header className="site-header"><a className="brand" href="#top" onClick={backToSearch}><span className="brand-mark" aria-hidden="true">📚</span><span>문화유산 AI 가이드</span></a>{user ? <div className="user"><b>{user.name}</b><button className="outline" onClick={logout}>로그아웃</button></div> : <button className="outline login-button" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}</header>
    {showingAnswer ? <AnswerView question={question} level={level} result={result} loading={loading} onBack={backToSearch} onChangeLevel={(nextLevel) => askQuestion(question, nextLevel)} onReport={() => { setReportError(""); setReportOpen(true); }} onAsk={(nextQuestion) => askQuestion(nextQuestion, level)} /> : <>
      <section className="hero" id="top"><div className="hero-inner"><p className="eyebrow">🏛️ AI 기반 문화유산 학습 서비스</p><h1>어떤 역사·문화 이야기가<br />궁금한가요?</h1><p className="hero-copy">문화유산과 역사에 대해 쉽고 믿을 수 있게 알아보세요.</p><form onSubmit={ask} className="question-box"><label className="question-row" htmlFor="question"><span aria-hidden="true">⌕</span><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="예: 경복궁은 왜 지어졌나요? 고려청자의 특징은?" aria-label="질문" /><button className="primary">질문하기</button></label><div className="level-row"><span>설명 수준:</span><div>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => setLevel(value)}>{label}</button>)}</div></div></form></div></section>
      <section className="section-shell stories-section"><div className="section-title"><div><h2>오늘의 이야기</h2><p>{today.label} · 오늘의 문화유산</p></div><button type="button" className="more" onClick={() => useQuestion("오늘의 문화유산을 소개해 줘")}>더 보기 →</button></div><div className="story-grid">{selectDailyStories(today.key).map((story, index) => <button key={story.title} className={`story-card ${index === 0 ? "featured" : ""}`} onClick={() => useQuestion(story.question)}><img className="story-image" src={story.image} alt={story.imageAlt} /><span className="story-copy">{index === 0 && <span className="story-badge">오늘의 추천</span>}<b>{story.title}</b><small>{story.subtitle}</small></span></button>)}</div></section>
      <section className="topics-section"><div className="section-shell"><h2>추천 주제</h2><div className="topic-list">{topics.map((topic) => <button key={topic} onClick={() => useQuestion(`${topic}에 대해 알려줘`)}>{topic}</button>)}</div><div className="stats"><span><b>12,480</b> 등록 문화유산</span><span><b>89,200+</b> 누적 질문 답변</span><span><b>98.3%</b> 정보 출처 보유율</span></div></div></section>
      {user && <section className="section-shell recent-section"><div className="section-title"><div><h2>사용자 최근 검색</h2><p>◷ {user.name} 계정에 저장됨</p></div></div>{recentSearches.length > 0 ? <div className="recent-list">{recentSearches.map((item) => <button key={item.id} onClick={() => useQuestion(item.question, item.audience_level)}><span>{item.question}</span><small><em>{levels.find(([value]) => value === item.audience_level)?.[1] || "중·고등학생"}</em>{relativeTime(item.created_at)}</small></button>)}</div> : <p className="empty-history">아직 검색 기록이 없습니다. 첫 질문을 남겨 보세요.</p>}</section>}
    </>}
    <footer><div className="footer-inner"><div><b>문화유산 AI 가이드</b><p>국가 문화유산 정보를 AI로 쉽게 알아보는 공공 서비스</p></div><nav><a href="#top">이용약관</a><a href="#top">개인정보 처리방침</a><a href="#top">오류 제보</a></nav></div></footer>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="이름" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일" type="email" value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
    {reportOpen && <div className="modal"><form onSubmit={submitReport}><button type="button" className="close" onClick={() => setReportOpen(false)}>×</button><h2>답변 오류 제보</h2><select value={reportCategory} onChange={(event) => setReportCategory(event.target.value)}><option value="incorrect_fact">사실이 틀림</option><option value="citation_mismatch">출처가 맞지 않음</option><option value="incomplete_answer">설명이 부족함</option><option value="inappropriate_content">부적절한 내용</option><option value="other">기타</option></select><textarea placeholder="10자 이상으로 내용을 작성해 주세요." value={reportContent} onChange={(event) => setReportContent(event.target.value)} minLength="10" maxLength="2000" required />{reportError && <p className="error">{reportError}</p>}<button className="primary">제보 보내기</button></form></div>}
  </main>;
}
