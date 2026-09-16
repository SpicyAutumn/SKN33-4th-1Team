import { useEffect, useState } from "react";

const levels = [["easy", "초등학생"], ["general", "중·고등학생"], ["advanced", "성인 일반"]];
const heritageStories = [
  {
    title: "경복궁 근정전", subtitle: "조선의 정치 중심지", question: "경복궁 근정전은 어떤 곳인가요?", featured: true,
    image: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Gyeongbokgung-GeunJeongJeon.jpg/1280px-Gyeongbokgung-GeunJeongJeon.jpg",
    imageAlt: "경복궁 근정전",
  },
  {
    title: "첨성대", subtitle: "신라의 천문 관측소", question: "첨성대는 어떻게 천문을 관측했나요?",
    image: "https://upload.wikimedia.org/wikipedia/commons/8/8f/Cheomseongdae_%EC%B2%A8%EC%84%B1%EB%8C%80.jpg",
    imageAlt: "경주 첨성대",
  },
  {
    title: "석굴암", subtitle: "통일신라의 불교 미술", question: "석굴암의 특징을 알려줘",
    image: "https://commons.wikimedia.org/wiki/Special:FilePath/Korea-Gyeongju-Seokguram%20grotto-Outside%20view-01.jpg?width=1280",
    imageAlt: "경주 석굴암",
  },
  {
    title: "창덕궁 인정전", subtitle: "왕실 의례가 열린 정전", question: "창덕궁 인정전은 어떤 곳인가요?",
    image: "https://commons.wikimedia.org/wiki/Special:FilePath/Changdeokgung-Injeongjeon.jpg?width=1280",
    imageAlt: "창덕궁 인정전",
  },
  {
    title: "불국사 다보탑", subtitle: "통일신라 석탑의 아름다움", question: "불국사 다보탑의 특징을 알려줘",
    image: "https://commons.wikimedia.org/wiki/Special:FilePath/Bulguksa_3.jpg?width=1280",
    imageAlt: "불국사 다보탑",
  },
  {
    title: "종묘 정전", subtitle: "조선 왕실 제례의 공간", question: "종묘 정전은 어떤 곳인가요?",
    image: "https://www.heritage.go.kr/gung/gogung5/images/img_jongmyo_story_bg_19_00.jpg",
    imageAlt: "종묘 정전",
  },
  {
    title: "수원 화성", subtitle: "정조가 세운 과학적 성곽", question: "수원 화성은 왜 지어졌나요?",
    image: "https://commons.wikimedia.org/wiki/Special:FilePath/Wall_of_Hwaseong_Fortress_in_Suwon%2C_South_Korea.jpg?width=1280",
    imageAlt: "수원 화성",
  },
];
const topics = ["조선 왕조", "불교 문화재", "유네스코 세계유산", "고려 청자", "한양 도성", "3·1 운동", "한글 창제", "왕릉과 능침"];
const recentSearches = [["경복궁은 언제 지어졌나요?", "초등학생", "10분 전", "easy"], ["고려청자와 조선백자의 차이", "성인 일반", "어제", "advanced"], ["훈민정음 창제 배경", "중·고등학생", "2일 전", "general"]];

const koreanDate = () => {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = Object.fromEntries(parts.filter(({ type }) => type !== "literal").map(({ type, value }) => [type, value]));
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

const api = async (path, options = {}) => {
  const response = await fetch(`/api/${path}`, { credentials: "include", headers: { "Content-Type": "application/json", ...options.headers }, ...options });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "요청을 처리하지 못했습니다.");
  return body;
};

export default function App() {
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
  const [today, setToday] = useState(koreanDate);

  useEffect(() => { api("auth/me").then(({ user }) => setUser(user)).catch(() => {}); }, []);
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
      const data = authMode === "signup" ? await api("auth/signup", { method: "POST", body: JSON.stringify({ username, email: identity, password }) }) : await api("auth/login", { method: "POST", body: JSON.stringify({ identity, password }) });
      setUser(data); setAuthMode(null); setIdentity(""); setUsername(""); setPassword("");
    } catch (error) { setAuthError(error.message); }
  };
  const ask = async (event) => {
    event.preventDefault(); setLoading(true); setResult(null);
    try { setResult(await api("chat", { method: "POST", body: JSON.stringify({ question, audience_level: level }) })); }
    catch (error) { setResult({ error: error.message }); }
    finally { setLoading(false); }
  };
  const useQuestion = (nextQuestion, nextLevel = level) => { setQuestion(nextQuestion); setLevel(nextLevel); document.querySelector("#question")?.focus(); };
  const logout = async () => { await api("auth/logout", { method: "POST" }); setUser(null); };

  return <main>
    <header className="site-header">
      <a className="brand" href="#top"><span className="brand-mark">문</span><span>문화유산 AI 가이드</span></a>
      {user ? <div className="user"><b>{user.username}</b><button className="outline" onClick={logout}>로그아웃</button></div> : <button className="outline login-button" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}
    </header>
    <section className="hero" id="top"><div className="hero-inner">
      <p className="eyebrow">🏛️ AI 기반 문화유산 학습 서비스</p><h1>어떤 역사·문화 이야기가<br />궁금한가요?</h1><p className="hero-copy">문화유산과 역사에 대해 쉽고 믿을 수 있게 알아보세요.</p>
      <form onSubmit={ask} className="question-box"><label className="question-row" htmlFor="question"><span aria-hidden="true">⌕</span><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="예: 경복궁은 왜 지어졌나요? 고려청자의 특징은?" aria-label="질문" /><button className="primary">질문하기</button></label><div className="level-row"><span>설명 수준:</span><div>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => setLevel(value)}>{label}</button>)}</div></div></form>
    </div></section>
    {(loading || result) && <section className="answer section-shell">{loading && <p className="loading">자료를 찾고 답변을 준비하고 있어요.</p>}{result && (result.error ? <p className="error">{result.error}</p> : <>{result.demo && <div className="demo">시연 모드</div>}<h2>질문에 대한 설명</h2><p className="answer-message">{result.message}</p><h3>답변의 근거 확인</h3>{result.citations.map((citation) => <article key={citation.source_url}><b>{citation.title}</b><p>{citation.content}</p><a href={citation.source_url} target="_blank" rel="noreferrer">원문 보기 ↗</a></article>)}</>)}</section>}
    <section className="section-shell stories-section"><div className="section-title"><div><h2>오늘의 이야기</h2><p>{today.label} · 오늘의 문화유산</p></div><button type="button" className="more" onClick={() => useQuestion("오늘의 문화유산을 소개해 줘")}>더 보기 →</button></div><div className="story-grid">{selectDailyStories(today.key).map((story, index) => <button key={story.title} className={`story-card ${index === 0 ? "featured" : ""}`} onClick={() => useQuestion(story.question)}><img className="story-image" src={story.image} alt={story.imageAlt} /><span className="story-copy">{index === 0 && <span className="story-badge">오늘의 추천</span>}<b>{story.title}</b><small>{story.subtitle}</small></span></button>)}</div></section>
    <section className="topics-section"><div className="section-shell"><h2>추천 주제</h2><div className="topic-list">{topics.map((topic) => <button key={topic} onClick={() => useQuestion(`${topic}에 대해 알려줘`)}>{topic}</button>)}</div><div className="stats"><span><b>12,480</b> 등록 문화유산</span><span><b>89,200+</b> 누적 질문 답변</span><span><b>98.3%</b> 정보 출처 보유율</span></div></div></section>
    <section className="section-shell recent-section"><div className="section-title"><div><h2>최근 검색</h2><p>◷ 이 브라우저에 저장됨</p></div></div><div className="recent-list">{recentSearches.map(([text, label, time, itemLevel]) => <button key={text} onClick={() => useQuestion(text, itemLevel)}><span>{text}</span><small><em>{label}</em>{time}</small></button>)}</div></section>
    <footer><div className="footer-inner"><div><b>문 문화유산 AI 가이드</b><p>국가 문화유산 정보를 AI로 쉽게 알아보는 공공 서비스</p></div><nav><a href="#top">이용약관</a><a href="#top">개인정보 처리방침</a><a href="#top">오류 제보</a></nav></div></footer>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="사용자명" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일 또는 사용자명" type={authMode === "signup" ? "email" : "text"} value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
  </main>;
}
