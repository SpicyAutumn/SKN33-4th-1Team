import { useEffect, useRef, useState } from 'react';
import photos from '../data/heritagePhotos.json';
import regions from '../data/heritagePreviewRegions.json';
import provincePaths from '../data/heritageProvincePaths.json';
import './HeritageLoading.css';

const shuffle = (avoid) => {
  const deck = [...photos];
  for (let i = deck.length - 1; i > 0; i -= 1) { const j = Math.floor(Math.random() * (i + 1)); [deck[i], deck[j]] = [deck[j], deck[i]]; }
  if (deck[0]?.id === avoid && deck.length > 1) [deck[0], deck[1]] = [deck[1], deck[0]];
  return deck;
};

export default function HeritageLoading() {
  const [tour, setTour] = useState(() => ({ deck: shuffle(), index: 0 }));
  const [paused, setPaused] = useState(false);
  const [failed, setFailed] = useState({});
  const area = useRef(null);
  const transition = useRef(null);
  const [changing, setChanging] = useState(false);
  const advance = () => {
    if (transition.current !== null) return;
    const next = () => {
      setTour(({ deck, index }) => index + 1 < deck.length ? { deck, index: index + 1 } : { deck: shuffle(deck[index].id), index: 0 });
      setChanging(false);
      transition.current = null;
    };
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { next(); return; }
    setChanging(true);
    transition.current = window.setTimeout(next, 450);
  };
  useEffect(() => () => window.clearTimeout(transition.current), []);
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const timer = window.setInterval(() => {
      if (paused || document.hidden || motion.matches || !area.current || area.current.matches(':hover') || area.current.contains(document.activeElement) || area.current.querySelector('details[open]')) return;
      advance();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [paused]);
  const photo = tour.deck[tour.index];
  const regionKey = photo.id.replace('-nature', '');
  const region = regions[regionKey];
  const east = ['gangwon', 'chungbuk', 'gyeongbuk', 'daegu', 'ulsan', 'busan', 'gyeongnam'].includes(regionKey);
  return <section ref={area} className="heritage-loading" aria-label="답변 준비">
    <p role="status" className="heritage-loading-status">자료를 찾고 답변을 준비하고 있어요.</p>
    <h2>기다리는 동안 만나는 우리 문화유산</h2>
    <p className="heritage-loading-hint">아래는 질문의 검색 결과와 무관한 문화·자연유산 소개입니다.</p>
    <div className={`heritage-loading-tour province-tour${changing ? ' is-changing' : ''}`}>
      <div className="heritage-loading-map"><svg viewBox="0 0 550 500" role="img" aria-label={`한반도 시도 안내 지도 · ${region?.label || photo.region}`}>
        {provincePaths.map((path, index) => <path key={index} d={path.d} className={path.region === regionKey ? 'selected-province' : ''} />)}
        {region && <g className="province-label"><rect x={region.point[0] - 47} y={region.point[1] - 20} width="94" height="20" rx="6" /><text x={region.point[0]} y={region.point[1] - 6} textAnchor="middle">{region.label}</text></g>}
      </svg></div>
      <figure className={`heritage-loading-photo province-photo ${east ? 'is-east' : 'is-west'}`}><div className="province-photo-frame">{!failed[photo.id] && <img src={photo.image} alt={photo.title} onError={() => setFailed((current) => ({ ...current, [photo.id]: true }))} />}</div>
        <figcaption><small>{region?.label || photo.region} · {photo.category}</small><h3>{photo.name}</h3><p>{photo.attribution} / {photo.copyright_display}</p><a href={photo.license_url} target="_blank" rel="noopener noreferrer">{photo.kogl_label}</a> · <a href={photo.source_page} target="_blank" rel="noopener noreferrer">사진 출처 ↗</a><details><summary>사진 설명</summary><p>{photo.description}</p></details></figcaption>
      </figure>
    </div>
    <p className="heritage-map-source">지도: <a href="https://www.naturalearthdata.com/about/terms-of-use/" target="_blank" rel="noopener noreferrer">Natural Earth · Public Domain</a> · 시·도 소개용 경계이며 최신 행정구역 변경·작은 도서는 차이가 있을 수 있습니다.</p>
    <div className="heritage-loading-controls"><span>{tour.index + 1} / {photos.length} · 무작위 소개 순서</span><button type="button" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? '자동 넘김 재개' : '자동 넘김 멈춤'}</button><button type="button" onClick={advance}>다음 문화유산</button></div>
  </section>;
}
