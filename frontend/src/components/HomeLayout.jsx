import TodayHeritage from './TodayHeritage';
import SearchHistory from './SearchHistory';
import './HomeLayout.css';

export default function HomeLayout({ user, historyProps, question, onQuestionChange, onSubmit, level, levels, onLevelChange, onAsk, dateLabel, onLogin }) {
  return <section className="home-layout" id="top">
    <div className="home-layout-grid">
      <div className="home-search-area">
        <p className="home-eyebrow">문화유산 AI 가이드</p>
        <h1>어떤 문화유산이 궁금하세요?</h1>
        <p className="home-lead">궁금했던 문화유산, 질문에서 시작해 보세요.</p>
        <form className="home-question-box" onSubmit={onSubmit}>
          <div className="home-question-row"><label className="evidence-sr-only" htmlFor="question">질문</label><input id="question" value={question} onChange={(event) => onQuestionChange(event.target.value)} placeholder="예: 경복궁은 왜 지어졌나요?" required maxLength={1000} /><button type="submit" className="primary">질문하기</button></div>
          <div className="home-levels"><span>설명 수준</span>{levels.map(([value, label]) => <button type="button" key={value} aria-pressed={value === level} onClick={() => onLevelChange(value)}>{label}</button>)}</div>
        </form>
        <TodayHeritage onAsk={onAsk} dateLabel={dateLabel} />
      </div>
      <aside className="home-sidebar" aria-label="개인 검색 기록">
        {user ? <SearchHistory key={user.id} {...historyProps} /> : <section className="home-signin-history"><h2>내 검색 기록</h2><p>로그인하면 이전 질문과 저장된 답변을 다시 볼 수 있어요.</p><button type="button" onClick={onLogin}>로그인 / 회원가입</button></section>}
      </aside>
    </div>

  </section>;
}
