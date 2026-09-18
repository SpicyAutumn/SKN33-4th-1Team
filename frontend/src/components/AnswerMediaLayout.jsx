import { useMemo, useState } from 'react';
import './AnswerMediaLayout.css';

const httpUrl = (value) => {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; }
};

// PR #16: media[{ document_id, article_title, images[] }]. Match documents, never question text.
export default function AnswerMediaLayout({ media, citations = [], children }) {
  const [failed, setFailed] = useState({});
  const [index, setIndex] = useState(0);
  const images = useMemo(() => {
    const seen = new Set();
    return (Array.isArray(media) ? media : []).flatMap((group) => {
      const citation = citations.find((item) => item.document_id && item.document_id === group?.document_id);
      if (!citation || !Array.isArray(group.images)) return [];
      return [...group.images].sort((a, b) => Number(b?.role === 'head') - Number(a?.role === 'head')).flatMap((photo) => {
        const url = httpUrl(photo?.url);
        if (!url || !/^KOGL[1-4]$/.test(photo?.kogl_type) || seen.has(url) || failed[url]) return [];
        seen.add(url);
        return [{ ...photo, url, articleTitle: group.article_title || citation.title, source: httpUrl(citation.source_url) }];
      });
    });
  }, [media, citations, failed]);
  const selectedIndex = Math.min(index, Math.max(0, images.length - 1));
  const photo = images[selectedIndex];
  return <div className={`answer-media-layout${photo ? ' has-media' : ''}`}>
    {photo && <figure className="answer-photo">
      <img src={photo.url} alt={photo.title || photo.articleTitle || '참고 자료 이미지'} decoding="async" onError={() => setFailed((current) => ({ ...current, [photo.url]: true }))} />
      <figcaption><b>{photo.title || photo.articleTitle}</b><p>{photo.attribution || '『한국민족문화대백과사전』'}</p>{photo.copyright_display && <p>{photo.copyright_display}</p>}
        <a href={`https://www.kogl.or.kr/info/licenseType${photo.kogl_type.slice(-1)}.do`} target="_blank" rel="noopener noreferrer">{photo.kogl_label || `공공누리 제${photo.kogl_type.slice(-1)}유형`}</a>
        {photo.source && <> · <a href={photo.source} target="_blank" rel="noopener noreferrer">자료 원문 ↗</a></>}
        {photo.description && <details><summary>사진·자료 설명</summary><p>{photo.description}</p></details>}
      </figcaption>
      {images.length > 1 && <nav aria-label="답변 사진 선택"><button type="button" onClick={() => setIndex((selectedIndex + images.length - 1) % images.length)}>이전 사진</button><span>{selectedIndex + 1} / {images.length}</span><button type="button" onClick={() => setIndex((selectedIndex + 1) % images.length)}>다음 사진</button></nav>}
    </figure>}
    <div className="answer-explanation">{children}</div>
  </div>;
}
