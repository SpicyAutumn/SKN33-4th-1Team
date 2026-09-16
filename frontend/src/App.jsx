import { useEffect, useState } from "react";

const levels = [
  ["easy", "초등학생"],
  ["general", "중·고등학생"],
  ["advanced", "성인 일반"],
];

const api = async (path, options = {}) => {
  const response = await fetch(`/api/${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
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
  const [question, setQuestion] = useState("경복궁의 특징을 쉽게 설명해 줘");
  const [level, setLevel] = useState("easy");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api("auth/me").then(({ user }) => setUser(user)).catch(() => {}); }, []);

  const submitAuth = async (event) => {
    event.preventDefault();
    setAuthError("");
    try {
      const data = authMode === "signup"
        ? await api("auth/signup", { method: "POST", body: JSON.stringify({ username, email: identity, password }) })
        : await api("auth/login", { method: "POST", body: JSON.stringify({ identity, password }) });
      setUser(data);
      setAuthMode(null);
      setIdentity(""); setUsername(""); setPassword("");
    } catch (error) { setAuthError(error.message); }
  };

  const ask = async (event) => {
    event.preventDefault();
    setLoading(true); setResult(null);
    try { setResult(await api("chat", { method: "POST", body: JSON.stringify({ question, audience_level: level }) })); }
    catch (error) { setResult({ error: error.message }); }
    finally { setLoading(false); }
  };

  const logout = async () => { await api("auth/logout", { method: "POST" }); setUser(null); };

  return <main>
    <header><a className="brand" href="#top"><span>文</span> 문화유산 AI 가이드</a>
      {user ? <div className="user"><b>{user.username}</b><button onClick={logout}>로그아웃</button></div>
        : <button className="outline" onClick={() => setAuthMode("login")}>로그인 / 회원가입</button>}</header>
    <section className="hero" id="top"><p className="eyebrow">🏛️ AI 기반 문화유산 학습 서비스</p><h1>어떤 역사·문화 이야기가<br />궁금한가요?</h1><p>문화유산과 역사에 대해 쉽고 믿을 수 있게 알아보세요.</p>
      <form onSubmit={ask} className="question-box"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="질문" />
        <div className="controls"><div>{levels.map(([value, label]) => <button type="button" key={value} className={value === level ? "selected" : ""} onClick={() => setLevel(value)}>{label}</button>)}</div><button className="primary">질문하기</button></div>
      </form></section>
    {loading && <section className="answer"><p>자료를 찾고 답변을 준비하고 있어요.</p></section>}
    {result && <section className="answer">{result.error ? <p className="error">{result.error}</p> : <><div className="demo">시연 모드</div><h2>질문에 대한 설명</h2><p>{result.message}</p><h3>답변의 근거 확인</h3>{result.citations.map((citation) => <article key={citation.source_url}><b>{citation.title}</b><p>{citation.content}</p><a href={citation.source_url} target="_blank" rel="noreferrer">원문 보기 ↗</a></article>)}</>}</section>}
    <section className="topics"><h2>추천 주제</h2>{["조선 왕조", "불교 문화재", "유네스코 세계유산", "고려 청자", "한글 창제"].map((topic) => <button key={topic} onClick={() => setQuestion(`${topic}에 대해 알려줘`)}>{topic}</button>)}</section>
    {authMode && <div className="modal"><form onSubmit={submitAuth}><button type="button" className="close" onClick={() => setAuthMode(null)}>×</button><h2>{authMode === "signup" ? "회원가입" : "로그인"}</h2>{authMode === "signup" && <input placeholder="사용자명" value={username} onChange={(event) => setUsername(event.target.value)} required />}<input placeholder="이메일 또는 사용자명" type={authMode === "signup" ? "email" : "text"} value={identity} onChange={(event) => setIdentity(event.target.value)} required /><input placeholder="비밀번호 (8자 이상)" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />{authError && <p className="error">{authError}</p>}<button className="primary">{authMode === "signup" ? "가입하고 시작하기" : "로그인"}</button><button type="button" className="link" onClick={() => setAuthMode(authMode === "signup" ? "login" : "signup")}>{authMode === "signup" ? "이미 계정이 있어요" : "계정 만들기"}</button></form></div>}
  </main>;
}
