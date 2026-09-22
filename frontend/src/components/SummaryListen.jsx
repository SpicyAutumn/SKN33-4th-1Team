import { useEffect, useRef, useState } from 'react';
import { createSummarySpeech } from './summarySpeech.js';
import './SummaryListen.css';

export default function SummaryListen({ text }) {
  const [state, setState] = useState({ playing: false, message: '' });
  const control = useRef(null);
  useEffect(() => {
    let active = true;
    const controller = createSummarySpeech({ synth: window.speechSynthesis,
      Utterance: window.SpeechSynthesisUtterance,
      update: (next) => { if (active) setState(next); } });
    control.current = controller;
    const hide = () => { if (document.hidden) controller.stop(); };
    const leave = () => controller.stop();
    document.addEventListener('visibilitychange', hide);
    window.addEventListener('pagehide', leave);
    return () => {
      active = false; controller.stop(); control.current = null;
      document.removeEventListener('visibilitychange', hide);
      window.removeEventListener('pagehide', leave);
    };
  }, [text]);
  return <span className="summary-listen">
    <button type="button" aria-pressed={state.playing} onClick={() => state.playing ? control.current?.stop() : control.current?.play(text)}>{state.playing ? '읽기 중지' : '요약 듣기'}</button>
    <span className="summary-listen-status" role="status">{state.message}</span>
  </span>;
}
