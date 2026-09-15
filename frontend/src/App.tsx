import { FormEvent, useEffect, useMemo, useState } from "react";

type Page = "home" | "answer" | "heritage" | "report" | "auth" | "my";
type Audience = "easy" | "general" | "advanced";
type Citation = { title: string; content: string; source_url: string; section?: string };
type ServiceResponse = {
  response_type: string;
  message: string;
  audience_level: Audience;
  citations: Citation[];
  clarification?: { question: string; options: { id: string; label: string }[] } | null;
  premise_correction?: { corrected_premise: string } | null;
};
type Execution = { response: ServiceResponse; retrieved_contexts?: Citation[] };
type HistoryItem = { question: string; level: Audience; createdAt: string };
type SavedItem = { title: string; subtitle: string };
type Report = { id: string; report_type: string; status: string; detail: string };
type Member = { id: number; username: string; email: string };

const audienceLabels: Record<Audience, string> = {
  easy: "초등학생",
  general: "중·고등학생",
  advanced: "성인 일반",
};
const exampleHistory: HistoryItem[] = [
  { question: "경복궁은 언제 지어졌나요?", level: "easy", createdAt: new Date(Date.now() - 10 * 60_000).toISOString() },
  { question: "고려청자와 조선백자의 차이", level: "advanced", createdAt: new Date(Date.now() - 86_400_000).toISOString() },
  { question: "훈민정음 창제 배경", level: "general", createdAt: new Date(Date.now() - 2 * 86_400_000).toISOString() },
];
const suggestedQuestions = [
  "경복궁의 특징은 무엇인가요?",
  "불국사가 중요한 이유를 알려줘",
  "훈민정음은 어떻게 만들어졌나요?",
];
const sampleCitation: Citation = {
  title: "경복궁",
  content: "경복궁은 조선 초기의 법궁으로 1395년에 창건되었다.",
  source_url: "https://encykorea.aks.ac.kr/",
  section: "정의",
};

function readStore<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored ? (JSON.parse(stored) as T) : fallback;
  } catch {
    return fallback;
  }
}

function getCookie(name: string) {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1] || "";
}

async function djangoRequest(path: string, body?: Record<string, string>) {
  await fetch("/django-api/accounts/api/csrf/", { credentials: "include" });
  return fetch(`/django-api${path}`, {
    method: body ? "POST" : "GET",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

function authError(payload: { detail?: string; errors?: Record<string, { message: string }[]> }) {
  if (payload.detail) return payload.detail;
  const first = payload.errors && Object.values(payload.errors)[0]?.[0]?.message;
  return first || "요청을 처리하지 못했습니다.";
}

function demoExecution(question: string, level: Audience): Execution {
  const prefix = level === "easy" ? "쉽게 말하면, " : level === "advanced" ? "조금 더 깊이 살펴보면, " : "";
  return {
    response: {
      response_type: "answered",
      message: `${prefix}‘${question}’에 관한 실제 RAG 응답은 서버 설정이 완료되면 표시됩니다. 현재는 화면 흐름을 확인하기 위한 시연 응답입니다. 답변에는 반드시 확인된 원문 근거가 함께 제공됩니다.`,
      audience_level: level,
      citations: [sampleCitation],
    },
  };
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric" }).format(new Date(value));
}

function relativeTime(value: string) {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  if (minutes < 60) return `${Math.max(1, minutes)}분 전`;
  if (minutes < 60 * 36) return "어제";
  if (minutes < 60 * 24 * 7) return `${Math.floor(minutes / (60 * 24))}일 전`;
  return formatDate(value);
}

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [question, setQuestion] = useState("");
  const [audience, setAudience] = useState<Audience>("general");
  const [execution, setExecution] = useState<Execution | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [member, setMember] = useState<Member | null>(null);
  const [history, setHistory] = useState(() => readStore<HistoryItem[]>("heritage-history", []));
  const [saved, setSaved] = useState(() => readStore<SavedItem[]>("heritage-saved", []));
  const [reports, setReports] = useState(() => readStore<Report[]>("heritage-reports", []));

  const currentResponse = execution?.response ?? null;
  const isSaved = saved.some((item) => item.title === "경복궁");
  const visibleHistory = useMemo(() => [
    ...history,
    ...exampleHistory.filter((example) => !history.some((item) => item.question === example.question)),
  ].slice(0, 3), [history]);

  useEffect(() => {
    djangoRequest("/accounts/api/me/").then(async (response) => {
      if (response.ok) setMember((await response.json() as { user: Member }).user);
    }).catch(() => undefined);
  }, []);

  function persist<T>(key: string, value: T) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  async function ask(nextQuestion = question, level = audience) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      setNotice("궁금한 내용을 입력해 주세요.");
      return;
    }
    setQuestion(trimmed);
    setAudience(level);
    setNotice("");
    setIsLoading(true);
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, audience_level: level }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || "질문을 처리하지 못했습니다.");
      setExecution((await response.json()) as Execution);
    } catch (error) {
      setExecution(demoExecution(trimmed, level));
      setNotice(error instanceof Error ? `${error.message} 시연 응답을 표시합니다.` : "시연 응답을 표시합니다.");
    } finally {
      setIsLoading(false);
      const nextHistory = [{ question: trimmed, level, createdAt: new Date().toISOString() }, ...history.filter((item) => item.question !== trimmed)].slice(0, 10);
      setHistory(nextHistory);
      persist("heritage-history", nextHistory);
      setPage("answer");
    }
  }

  function toggleSaved() {
    const next = isSaved ? saved.filter((item) => item.title !== "경복궁") : [...saved, { title: "경복궁", subtitle: "조선의 법궁 · 서울 종로구" }];
    setSaved(next);
    persist("heritage-saved", next);
    setNotice(isSaved ? "저장 목록에서 삭제했습니다." : "경복궁을 저장했습니다.");
  }

  async function submitReport(type: string, detail: string) {
    if (!currentResponse || detail.trim().length < 3) {
      setNotice("확인할 부분을 세 글자 이상 적어 주세요.");
      return;
    }
    const payload = { question, answer_summary: currentResponse.message, report_type: type, detail };
    let report: Report;
    try {
      const response = await fetch("/api/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error();
      report = (await response.json()) as Report;
    } catch {
      report = { id: `LOCAL-${Date.now().toString().slice(-5)}`, report_type: type, status: "접수됨", detail };
    }
    const next = [report, ...reports];
    setReports(next);
    persist("heritage-reports", next);
    setNotice("제보를 접수했습니다. 현재는 이 브라우저에서 확인할 수 있습니다.");
    setPage("my");
  }

  async function signIn(mode: "login" | "signup", values: Record<string, string>) {
    const path = mode === "signup" ? "/accounts/api/signup/" : "/accounts/api/login/";
    const response = await djangoRequest(path, values);
    const payload = await response.json() as { user?: Member; detail?: string; errors?: Record<string, { message: string }[]> };
    if (!response.ok || !payload.user) throw new Error(authError(payload));
    setMember(payload.user);
    localStorage.removeItem("heritage-member");
    setNotice(mode === "signup" ? "회원가입이 완료되었습니다." : "로그인했습니다.");
    setPage("my");
  }

  async function signOut() {
    try { await djangoRequest("/accounts/api/logout/", {}); } finally {
      setMember(null);
      setNotice("로그아웃했습니다.");
      setPage("home");
    }
  }

  const header = (
    <header className="topbar">
      <button className="brand" onClick={() => setPage("home")} aria-label="홈으로 이동"><span>문</span> 문화유산 AI 가이드</button>
      <nav aria-label="주요 메뉴">
        <button onClick={() => setPage("heritage")}>문화유산 둘러보기</button>
        <button onClick={() => setPage("home")}>오늘의 이야기</button>
        <button onClick={() => setPage("my")}>내 기록</button>
      </nav>
      <button className="member-button" onClick={() => setPage(member ? "my" : "auth")}>{member ? `${member.username} 님` : "로그인 / 회원가입"}</button>
    </header>
  );

  return (
    <div className="app-shell">
      {header}
      {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")}>닫기</button></div>}
      {page === "home" && <Home question={question} audience={audience} history={visibleHistory} member={member} loading={isLoading} onQuestion={setQuestion} onAudience={setAudience} onAsk={ask} onOpenHistory={(item) => ask(item.question, item.level)} />}
      {page === "answer" && <Answer response={currentResponse} question={question} audience={audience} loading={isLoading} onAudience={(level) => ask(question, level)} onHeritage={() => setPage("heritage")} onReport={() => setPage("report")} onAsk={ask} />}
      {page === "heritage" && <Heritage saved={isSaved} onSave={toggleSaved} onAsk={() => ask("경복궁에 대해 쉽게 설명해 주세요.", "easy")} onBack={() => setPage("answer")} />}
      {page === "report" && <ReportPage question={question} response={currentResponse} onCancel={() => setPage("answer")} onSubmit={submitReport} />}
      {page === "auth" && <AuthPage onSubmit={signIn} onBack={() => setPage("home")} />}
      {page === "my" && <MyPage member={member} history={history} saved={saved} reports={reports} onAuth={() => setPage("auth")} onAsk={(item) => ask(item.question, item.level)} onHeritage={() => setPage("heritage")} onLogout={signOut} />}
      <footer><div><strong>문화유산 AI 가이드</strong><span>국가 문화유산 정보를 AI로 쉽게 알아보는 공공 서비스</span></div><div className="footer-links"><button>이용약관</button><button>개인정보 처리방침</button><button onClick={() => setPage("report")}>오류 제보</button></div></footer>
    </div>
  );
}

function Home(props: { question: string; audience: Audience; history: HistoryItem[]; member: Member | null; loading: boolean; onQuestion: (value: string) => void; onAudience: (value: Audience) => void; onAsk: (question?: string, audience?: Audience) => void; onOpenHistory: (item: HistoryItem) => void }) {
  function submit(event: FormEvent) { event.preventDefault(); props.onAsk(); }
  return <main>
    <section className="hero-section">
      <div className="hero-copy"><p className="eyebrow">🏛️ AI 기반 문화유산 학습 서비스</p><h1>어떤 역사·문화 이야기가<br />궁금한가요?</h1><p>문화유산과 역사에 대해 쉽고 믿을 수 있게 알아보세요.</p>
        <form className="question-form" onSubmit={submit}><span className="search-symbol">⌕</span><input value={props.question} onChange={(event) => props.onQuestion(event.target.value)} placeholder="예: 경복궁은 왜 지어졌나요? 고려청자의 특징은?" aria-label="문화유산 질문" /><button disabled={props.loading}>{props.loading ? "답변 준비 중…" : "질문하기"}</button></form>
        <div className="level-selector"><span>설명 수준:</span>{(Object.keys(audienceLabels) as Audience[]).map((level) => <button key={level} className={props.audience === level ? "selected" : ""} onClick={() => props.onAudience(level)}>{audienceLabels[level]}</button>)}<button className="expert-level" onClick={() => props.onAudience("advanced")}>전문가</button></div>
      </div>
    </section>
    <section className="content-section stories"><div className="section-title"><div><h2>오늘의 이야기</h2><p>2026년 9월 14일 · 오늘의 문화유산</p></div><button className="text-link">더 보기 →</button></div><div className="story-grid">
      {[['경복궁 근정전', '조선의 정치 중심지', 'https://images.unsplash.com/photo-1638964663550-e2123ac8900b?w=400&h=280&fit=crop&auto=format'], ['첨성대', '신라의 천문 관측소', 'https://images.unsplash.com/photo-1599033769063-fcd3ef816810?w=400&h=280&fit=crop&auto=format'], ['석굴암', '통일신라의 불교 미술', 'https://images.unsplash.com/photo-1602479185195-32f5cd203559?w=400&h=280&fit=crop&auto=format']].map(([title, subtitle, image], index) => <button className="story-card" key={title} onClick={() => props.onAsk(`${title}에 대해 알려줘`, props.audience)}><div className="heritage-image"><img src={image} alt={title} />{index === 0 && <small>오늘의 추천</small>}</div><div className="story-copy"><h3>{title}</h3><p>{subtitle}</p></div></button>)}</div></section>
    <section className="content-section dashboard"><section><h2>추천 주제</h2><div className="topic-cloud">{['조선 왕조', '불교 문화재', '유네스코 세계유산', '고려 청자', '한양 도성', '3·1 운동', '한글 창제', '왕릉과 능침'].map((topic) => <button key={topic} onClick={() => props.onAsk(`${topic}에 대해 알려줘`, props.audience)}>{topic}</button>)}</div><div className="metrics"><div><b>12,480</b><span>등록 문화유산</span></div><div><b>89,200+</b><span>누적 질문 답변</span></div><div><b>98.3%</b><span>정보 출처 보유율</span></div></div></section><aside className="recent"><div className="section-title"><div><h2>최근 검색</h2></div><span className="history-chip">◷ {props.member ? '내 계정에 저장됨' : '이 브라우저에 저장됨'}</span></div><div className="history-list">{props.history.map((item) => <button key={item.createdAt} onClick={() => props.onOpenHistory(item)}><span>{item.question}</span><small>{audienceLabels[item.level]} · {relativeTime(item.createdAt)}</small><b>→</b></button>)}</div></aside></section>
  </main>;
}

function Answer(props: { response: ServiceResponse | null; question: string; audience: Audience; loading: boolean; onAudience: (audience: Audience) => void; onHeritage: () => void; onReport: () => void; onAsk: (question: string, audience: Audience) => void }) {
  const response = props.response;
  if (props.loading) return <main className="state-page"><div className="spinner" /><h2>공식 자료를 확인하고 있습니다.</h2><p>검색된 근거를 바탕으로 답변을 준비 중입니다.</p></main>;
  if (!response) return <main className="state-page"><h2>아직 답변이 없습니다.</h2><button className="primary" onClick={() => props.onAsk('경복궁의 특징을 알려줘', 'general')}>예시 질문하기</button></main>;
  const clarification = response.clarification;
  return <main className="answer-page content-section"><button className="back-link" onClick={() => history.back()}>← 검색으로 돌아가기</button><p className="eyebrow dark">AI ANSWER</p><h1>{props.question}</h1><div className="answer-toolbar"><span className="badge">{audienceLabels[props.audience]}</span><div>{(Object.keys(audienceLabels) as Audience[]).map((level) => <button key={level} className="small-button" disabled={level === props.audience} onClick={() => props.onAudience(level)}>{audienceLabels[level]}로 보기</button>)}</div></div>
    <section className={`answer-card ${response.response_type !== 'answered' ? 'attention' : ''}`}><p className="card-label">{response.response_type === 'answered' ? 'AI가 생성한 설명' : '안내'}</p>{response.premise_correction && <div className="correction">확인된 내용: {response.premise_correction.corrected_premise}</div>}<p className="answer-message">{response.message}</p>{response.response_type === 'answered' && <div className="key-points"><div>① 선택한 수준에 맞춰 설명합니다.</div><div>② 확인된 원문 근거를 함께 보여 줍니다.</div><div>③ 근거가 부족하면 추측하지 않습니다.</div></div>}</section>
    {clarification && <section className="clarification"><h2>{clarification.question}</h2><div>{clarification.options.map((option) => <button key={option.id} onClick={() => props.onAsk(`${option.label}에 대해 알려줘`, props.audience)}>{option.label}</button>)}</div></section>}
    {!!response.citations.length && <section className="evidence"><p className="eyebrow dark">EVIDENCE</p><h2>근거 확인</h2>{response.citations.map((citation) => <article className="citation" key={`${citation.title}-${citation.content}`}><div><small>원문 근거 · {citation.section || '본문'}</small><h3>{citation.title}</h3><p>“{citation.content}”</p></div><a href={citation.source_url} target="_blank" rel="noreferrer">원문 열기 ↗</a></article>)}</section>}
    <section className="related-card"><div className="mini-image">景福宮</div><div><small>관련 문화유산</small><h2>경복궁</h2><p>조선 왕조의 법궁으로, 국가 의례와 정치의 중심이었던 궁궐입니다.</p></div><button onClick={props.onHeritage}>상세 보기 →</button></section>
    <div className="answer-actions"><button className="primary" onClick={() => props.onAsk(`${props.question}와 관련해 더 알아볼 내용을 알려줘`, props.audience)}>이어서 질문하기</button><button className="outline" onClick={props.onReport}>문제·오류 신고</button></div>
  </main>;
}

function Heritage(props: { saved: boolean; onSave: () => void; onAsk: () => void; onBack: () => void }) { return <main className="detail-page content-section"><button className="back-link" onClick={props.onBack}>← 검색 결과로 돌아가기</button><p className="eyebrow dark">HERITAGE DETAIL</p><div className="detail-title"><div><h1>경복궁</h1><p>조선 왕조의 법궁</p></div><button className={props.saved ? "saved-button" : "outline"} onClick={props.onSave}>{props.saved ? '★ 저장됨' : '☆ 저장하기'}</button></div><div className="detail-image"><span>景福宮</span><p>경복궁 근정전 · 이미지 자리</p></div><p className="image-caption">대표 이미지 · 출처와 이용 조건은 실제 문화유산 데이터 연결 후 표시됩니다.</p><div className="info-grid"><article><small>시대</small><b>조선</b></article><article><small>위치</small><b>서울특별시 종로구</b></article><article><small>지정 정보</small><b>사적</b></article></div><section className="detail-section"><h2>자료에서 확인된 정보</h2><p>경복궁은 조선 초기의 법궁으로 창건되었으며, 왕실의 주요 의례와 정치가 이루어진 공간입니다.</p><a href="https://encykorea.aks.ac.kr/" target="_blank" rel="noreferrer">한국민족문화대백과사전 원문 열기 ↗</a></section><section className="detail-section soft"><h2>AI가 쉽게 풀어 쓴 설명</h2><p>경복궁은 조선 시대 임금이 나라를 다스리던 중심 궁궐이에요. 중요한 손님을 맞이하고 국가 행사를 열던 장소이기도 했습니다.</p></section><div className="answer-actions"><button className="primary" onClick={props.onAsk}>이 항목을 쉽게 설명해 줘</button><button className="outline" onClick={props.onAsk}>이 항목에 대해 질문하기</button></div></main>; }

function ReportPage(props: { question: string; response: ServiceResponse | null; onCancel: () => void; onSubmit: (type: string, detail: string) => void }) { const [type, setType] = useState("내용 오류"); const [detail, setDetail] = useState(""); return <main className="form-page content-section"><p className="eyebrow dark">REPORT</p><h1>이 답변에서 어떤 문제가 있었나요?</h1><p>알려주신 내용은 답변 품질을 개선하는 데 사용됩니다.</p><div className="report-target"><small>신고 대상 질문</small><b>{props.question || '선택된 질문 없음'}</b><small>신고 대상 답변</small><p>{props.response?.message || '답변을 먼저 확인해 주세요.'}</p></div><fieldset><legend>오류 유형</legend>{['내용 오류', '근거·출처 문제', '사진 문제', '기타'].map((item) => <label key={item}><input type="radio" name="type" checked={type === item} onChange={() => setType(item)} />{item}</label>)}</fieldset><label className="textarea-label">구체적으로 알려 주세요<textarea value={detail} onChange={(event) => setDetail(event.target.value)} placeholder="어떤 부분을 확인하면 좋을지 적어 주세요." /></label><div className="answer-actions"><button className="outline" onClick={props.onCancel}>취소</button><button className="primary" onClick={() => props.onSubmit(type, detail)}>접수</button></div></main>; }

function LegacyAuthPage(props: { onSubmit: (name: string) => void; onBack: () => void }) { const [tab, setTab] = useState<"login" | "signup">("login"); const [name, setName] = useState(""); return <main className="auth-page"><section className="auth-card"><button className="back-link" onClick={props.onBack}>← 홈으로</button><p className="eyebrow dark">ACCOUNT</p><h1>{tab === 'login' ? '로그인' : '회원가입'}</h1><p>기록을 여러 기기에서 이어 보고, 저장한 문화유산과 제보 이력을 관리하세요.</p><div className="auth-tabs"><button className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')}>로그인</button><button className={tab === 'signup' ? 'active' : ''} onClick={() => setTab('signup')}>회원가입</button></div>{tab === 'signup' && <label>이름<input value={name} onChange={(event) => setName(event.target.value)} placeholder="이름을 입력하세요" /></label>}<label>이메일<input type="email" placeholder="name@example.com" /></label><label>비밀번호<input type="password" placeholder="8자 이상 입력하세요" /></label><button className="primary wide" onClick={() => props.onSubmit(name)}>{tab === 'login' ? '시연용 로그인' : '시연용 회원가입'}</button><p className="auth-note">현재는 화면 시연 단계입니다. 입력한 계정 정보는 서버에 저장되지 않습니다.</p><div className="benefits"><b>회원이 되면</b><span>최근 검색을 여러 기기에서 이어보기</span><span>저장한 문화유산 모아보기</span><span>내 오류 제보 처리 상태 확인</span></div></section></main>; }

function LegacyMyPage(props: { member: { name: string } | null; history: HistoryItem[]; saved: SavedItem[]; reports: Report[]; onAuth: () => void; onAsk: (item: HistoryItem) => void; onHeritage: () => void; onLogout: () => void }) { const [tab, setTab] = useState<'history' | 'saved' | 'reports'>('history'); if (!props.member) return <main className="state-page"><p className="eyebrow dark">MY RECORD</p><h1>내 기록을 관리하려면<br />로그인이 필요합니다.</h1><p>최근 질문, 저장한 문화유산, 오류 제보 이력은 회원 계정과 연결됩니다.</p><button className="primary" onClick={props.onAuth}>로그인 / 회원가입</button></main>; return <main className="my-page content-section"><p className="eyebrow dark">MY PAGE</p><div className="profile"><div className="avatar">문</div><div><h1>{props.member.name} 님</h1><p>시연용 로그인 상태 · 실제 계정 연결 전</p></div><button className="outline" onClick={props.onLogout}>로그아웃</button></div><div className="my-tabs">{([['history','최근 질문'], ['saved','저장한 문화유산'], ['reports','내 오류 제보']] as const).map(([key,label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>{tab === 'history' && <div className="record-list">{props.history.length ? props.history.map((item) => <article key={item.createdAt}><div><b>{item.question}</b><small>{audienceLabels[item.level]} · {formatDate(item.createdAt)}</small></div><button onClick={() => props.onAsk(item)}>이전 답변 열기</button></article>) : <p className="empty">아직 저장된 질문이 없습니다.</p>}</div>}{tab === 'saved' && <div className="record-list">{props.saved.length ? props.saved.map((item) => <article key={item.title}><div><b>{item.title}</b><small>{item.subtitle}</small></div><button onClick={props.onHeritage}>상세 보기</button></article>) : <p className="empty">문화유산 상세 화면에서 저장하기를 누르면 여기에 모입니다.</p>}</div>}{tab === 'reports' && <div className="record-list">{props.reports.length ? props.reports.map((item) => <article key={item.id}><div><b>{item.id} · {item.report_type}</b><small>{item.detail}</small></div><span className="badge">{item.status}</span></article>) : <p className="empty">아직 접수한 제보가 없습니다.</p>}</div>}</main>; }

function AuthPage(props: { onSubmit: (mode: "login" | "signup", values: Record<string, string>) => Promise<void>; onBack: () => void }) {
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setLoading(true); try { await props.onSubmit(tab, tab === "signup" ? { username, email: identifier, password1: password, password2 } : { identifier, password }); } catch (reason) { setError(reason instanceof Error ? reason.message : "로그인에 실패했습니다."); } finally { setLoading(false); } }
  return <main className="auth-page"><section className="auth-card"><button className="back-link" onClick={props.onBack}>← 홈으로</button><p className="eyebrow dark">ACCOUNT</p><h1>{tab === "login" ? "로그인" : "회원가입"}</h1><p>기록을 여러 기기에서 이어 보고, 저장한 문화유산과 제보 이력을 관리하세요.</p><div className="auth-tabs"><button className={tab === "login" ? "active" : ""} onClick={() => setTab("login")}>로그인</button><button className={tab === "signup" ? "active" : ""} onClick={() => setTab("signup")}>회원가입</button></div><form onSubmit={submit}>{tab === "signup" && <label>아이디<input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="영문·숫자 아이디" required /></label>}<label>{tab === "login" ? "아이디 또는 이메일" : "이메일"}<input type={tab === "login" ? "text" : "email"} value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder={tab === "login" ? "아이디 또는 name@example.com" : "name@example.com"} required /></label><label>비밀번호<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="8자 이상 입력하세요" required /></label>{tab === "signup" && <label>비밀번호 확인<input type="password" value={password2} onChange={(event) => setPassword2(event.target.value)} placeholder="비밀번호를 한 번 더 입력하세요" required /></label>}{error && <p className="auth-error">{error}</p>}<button className="primary wide" disabled={loading} type="submit">{loading ? "처리 중…" : tab === "login" ? "로그인" : "회원가입"}</button></form><p className="auth-note">입력한 계정은 Django 서버와 MySQL에 저장됩니다.</p><div className="benefits"><b>회원이 되면</b><span>최근 검색을 여러 기기에서 이어보기</span><span>저장한 문화유산 모아보기</span><span>내 오류 제보 처리 상태 확인</span></div></section></main>;
}

function MyPage(props: { member: Member | null; history: HistoryItem[]; saved: SavedItem[]; reports: Report[]; onAuth: () => void; onAsk: (item: HistoryItem) => void; onHeritage: () => void; onLogout: () => void }) {
  const [tab, setTab] = useState<'history' | 'saved' | 'reports'>('history');
  if (!props.member) return <main className="state-page"><p className="eyebrow dark">MY RECORD</p><h1>내 기록을 관리하려면<br />로그인이 필요합니다.</h1><p>최근 질문, 저장한 문화유산, 오류 제보 이력은 회원 계정과 연결됩니다.</p><button className="primary" onClick={props.onAuth}>로그인 / 회원가입</button></main>;
  return <main className="my-page content-section"><p className="eyebrow dark">MY PAGE</p><div className="profile"><div className="avatar">문</div><div><h1>{props.member.username} 님</h1><p>{props.member.email} · 실제 회원 계정 연결됨</p></div><button className="outline" onClick={props.onLogout}>로그아웃</button></div><div className="my-tabs">{([['history','최근 질문'], ['saved','저장한 문화유산'], ['reports','내 오류 제보']] as const).map(([key,label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>{tab === 'history' && <div className="record-list">{props.history.length ? props.history.map((item) => <article key={item.createdAt}><div><b>{item.question}</b><small>{audienceLabels[item.level]} · {formatDate(item.createdAt)}</small></div><button onClick={() => props.onAsk(item)}>이전 답변 열기</button></article>) : <p className="empty">아직 저장된 질문이 없습니다.</p>}</div>}{tab === 'saved' && <div className="record-list">{props.saved.length ? props.saved.map((item) => <article key={item.title}><div><b>{item.title}</b><small>{item.subtitle}</small></div><button onClick={props.onHeritage}>상세 보기</button></article>) : <p className="empty">문화유산 상세 화면에서 저장하기를 누르면 여기에 모입니다.</p>}</div>}{tab === 'reports' && <div className="record-list">{props.reports.length ? props.reports.map((item) => <article key={item.id}><div><b>{item.id} · {item.report_type}</b><small>{item.detail}</small></div><span className="badge">{item.status}</span></article>) : <p className="empty">아직 접수한 제보가 없습니다.</p>}</div>}</main>;
}
