import { useEffect, useRef, useState } from 'react';
import photos from '../data/todayHeritagePhotos';
import './TodayHeritage.css';

function nextPhotos(previous) {
  const oldIds = new Set(previous.map((photo) => photo.id));
  const candidates = photos.filter((photo) => !oldIds.has(photo.id));
  for (let i = candidates.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
  }
  return candidates.slice(0, 3);
}

function TodayCards({ items, failedImages, onImageError, onAsk }) {
  return items.map((photo, index) => <article className="today-card" key={photo.id} style={{ '--today-card-index': index }}>
    <button type="button" className="today-ask" onClick={() => onAsk(`${photo.article_title || photo.name}의 위치와 특징은 무엇인가요?`)}>
      <span className="today-photo">{!failedImages[photo.id] ? <img src={photo.image} alt={photo.title} loading="lazy" decoding="async" width="320" height="180" onError={() => onImageError(photo.id)} /> : <span className="today-photo-fallback">{photo.name}</span>}</span>
      <span className="today-copy"><small>{photo.region} · {photo.category}</small><b>{photo.name}</b><span>질문으로 알아보기 →</span></span>
    </button>
    <div className="today-credit"><p>{photo.attribution}</p><p>{photo.copyright_display}</p><a href={photo.license_url} target="_blank" rel="noopener noreferrer">{photo.kogl_label}</a><span> · </span><a href={photo.source_page} target="_blank" rel="noopener noreferrer">사진 출처 ↗</a><details><summary>사진 설명</summary><p>{photo.description}</p></details></div>
  </article>);
}

export default function TodayHeritage({ onAsk, dateLabel }) {
  const [selected, setSelected] = useState(() => nextPhotos([]));
  const [leaving, setLeaving] = useState(null);
  const [paused, setPaused] = useState(false);
  const [failedImages, setFailedImages] = useState({});
  const area = useRef(null);
  const rotate = () => setSelected((previous) => {
    setLeaving(previous);
    return nextPhotos(previous);
  });
  useEffect(() => {
    if (!leaving) return undefined;
    const timer = window.setTimeout(() => setLeaving(null), 560);
    return () => window.clearTimeout(timer);
  }, [leaving]);
  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const timer = window.setInterval(() => {
      const element = area.current;
      if (!element || paused || document.hidden || reducedMotion.matches || element.matches(':hover') || element.contains(document.activeElement) || element.querySelector('details[open]')) return;
      const bounds = element.getBoundingClientRect();
      if (bounds.bottom <= 0 || bounds.top >= window.innerHeight) return;
      rotate();
    }, 10000);
    return () => window.clearInterval(timer);
  }, [paused]);
  return <section ref={area} className="today-heritage" aria-label="오늘의 문화유산">
    <div className="today-heading"><div><h2>오늘의 문화유산</h2><p>{dateLabel} · 문화·자연유산을 세 곳씩 소개해요.</p></div><button type="button" className="today-pause" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? '자동 전환 재개' : '자동 전환 멈춤'}</button></div>
    <div className="today-cards-stage">
      {leaving && <div className="today-cards today-cards--leaving" aria-hidden="true" inert=""><TodayCards items={leaving} failedImages={failedImages} onImageError={() => {}} onAsk={onAsk} /></div>}
      <div className="today-cards today-cards--current"><TodayCards items={selected} failedImages={failedImages} onImageError={(id) => setFailedImages((current) => ({ ...current, [id]: true }))} onAsk={onAsk} /></div>
    </div>
  </section>;
}
