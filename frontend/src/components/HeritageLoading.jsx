import { useEffect, useRef, useState } from 'react';
import photos from '../data/heritagePhotos.json';
import points from '../data/heritageMapPoints.json';
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
  const advance = () => setTour(({ deck, index }) => index + 1 < deck.length ? { deck, index: index + 1 } : { deck: shuffle(deck[index].id), index: 0 });
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const timer = window.setInterval(() => {
      if (paused || document.hidden || motion.matches || !area.current || area.current.matches(':hover') || area.current.contains(document.activeElement)) return;
      advance();
    }, 6000);
    return () => window.clearInterval(timer);
  }, [paused]);
  const photo = tour.deck[tour.index];
  const point = points.find((item) => item.id === photo.id);
  return <section ref={area} className="heritage-loading" aria-label="답변 준비">
    <p role="status" className="heritage-loading-status">자료를 찾고 답변을 준비하고 있어요.</p>
    <h2>기다리는 동안 만나는 우리 문화유산</h2>
    <p className="heritage-loading-hint">아래는 질문의 검색 결과와 무관한 문화·자연유산 소개입니다.</p>
    <div className="heritage-loading-tour">
      <div className="heritage-loading-map"><svg viewBox="130 30 250 285" role="img" aria-label={`대한민국 지역 위치 개념도 · ${photo.region}`}>
        <path d="M262 54 L291 63 307 84 314 112 330 138 346 159 349 186 337 207 315 223 297 229 284 244 269 243 265 258 250 250 246 235 231 231 233 215 218 214 221 196 232 180 225 167 238 154 234 139 249 129 246 112 255 99 247 85Z" fill="#dce7d5" />
        <ellipse cx="244" cy="287" rx="23" ry="8" fill="#dce7d5" />
        {points.map((item) => <circle key={item.id} cx={item.x} cy={item.y} r="3" fill="#a7bba3" />)}
        {point && <circle cx={point.x} cy={point.y} r="8" fill="#285b48" />}
      </svg><small>지역 위치 개념도 · 실제 좌표 아님</small></div>
      <figure className="heritage-loading-photo">{!failed[photo.id] && <img src={photo.image} alt={photo.title} onError={() => setFailed((current) => ({ ...current, [photo.id]: true }))} />}
        <figcaption><small>{photo.region} · {photo.category}</small><h3>{photo.name}</h3><p>{photo.attribution} / {photo.copyright_display}</p><a href={photo.license_url} target="_blank" rel="noopener noreferrer">{photo.kogl_label}</a> · <a href={photo.source_page} target="_blank" rel="noopener noreferrer">사진 출처 ↗</a><p>{photo.description}</p></figcaption>
      </figure>
    </div>
    <div className="heritage-loading-controls"><span>{tour.index + 1} / {photos.length} · 무작위 소개 순서</span><button type="button" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? '자동 넘김 재개' : '자동 넘김 멈춤'}</button><button type="button" onClick={advance}>다음 문화유산</button></div>
  </section>;
}
