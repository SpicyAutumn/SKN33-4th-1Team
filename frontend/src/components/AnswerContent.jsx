import { answerSections } from "./answerSections.js";
import "./AnswerContent.css";
import SummaryListen from './SummaryListen';
import { summaryToRead } from './summarySpeech.js';
import { displayParagraphs } from './displayParagraphs.js';

export default function AnswerContent({ result, answerRef }) {
  const sections = answerSections(result);
  const speechKind = summaryToRead(result, sections);
  if (!sections.length) return <p className="answer-content-empty">표시할 답변이 없습니다. 다시 질문해 주세요.</p>;
  return <div className="answer-content">
    {sections.map(({ kind, title, text }) => <section className={`answer-content-section answer-content-${kind}`} key={kind} aria-label={title}>
      <h3>{title}{kind === speechKind && <SummaryListen key={result.request_id || result.search_record_id || text} text={text} />}</h3>
      <p ref={text === result.message ? answerRef : undefined}>{kind === 'message' && ['answered', 'corrected_premise'].includes(result.response_type)
        ? renderParagraphs(text) : text}</p>
    </section>)}
  </div>;
}

function renderParagraphs(text) {
  const parts = displayParagraphs(text);
  return parts.length === 1 ? text : parts.map((part, index) => <span className="answer-display-paragraph" key={index}>{part}</span>);
}
