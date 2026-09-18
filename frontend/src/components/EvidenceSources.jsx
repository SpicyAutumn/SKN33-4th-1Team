import './EvidenceSources.css';

const AKS_HOST = 'encykorea.aks.ac.kr';

function sourceUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url : null;
  } catch {
    return null;
  }
}

export default function EvidenceSources({ citations = [] }) {
  if (!citations.length) return null;
  return <section className="evidence-sources" aria-label="답변의 근거">
    <h2>답변의 근거</h2>
    <p className="evidence-intro">참고한 자료의 출처와 원문을 확인하세요.</p>
    <div className="evidence-source-list">{citations.map((citation, index) => {
      const url = sourceUrl(citation.source_url);
      const isAks = url?.hostname === AKS_HOST;
      const title = citation.title?.trim();
      return <article className="evidence-source" key={`${citation.chunk_id || citation.document_id || 'source'}-${index}`}>
        <p className="evidence-attribution">
          <span className="evidence-item-title">{title ? `[${title}]${isAks ? ',' : ''}` : '항목명 미제공'}</span>
          {isAks && <span>『한국민족문화대백과사전』</span>}
        </p>
        {url ? <a href={url.href} target="_blank" rel="noopener noreferrer">원문 보기 ↗<span className="evidence-sr-only"> · 새 탭에서 열림</span></a> : <span className="evidence-unavailable">원문 링크가 제공되지 않았습니다.</span>}
        {citation.content && <details>
          <summary>근거 내용 펼치기</summary>
          <p className="evidence-excerpt">{citation.content}</p>
        </details>}
      </article>;
    })}</div>
  </section>;
}
