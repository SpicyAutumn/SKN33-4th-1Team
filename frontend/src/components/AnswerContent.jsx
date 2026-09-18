import { answerSections } from "./answerSections.js";
import "./AnswerContent.css";

export default function AnswerContent({ result }) {
  const sections = answerSections(result);
  if (!sections.length) return <p className="answer-content-empty">표시할 답변이 없습니다. 다시 질문해 주세요.</p>;
  return <div className="answer-content">
    {sections.map(({ kind, title, text }) => <section className={`answer-content-section answer-content-${kind}`} key={kind} aria-label={title}>
      <h3>{title}</h3>
      <p>{text}</p>
    </section>)}
  </div>;
}
