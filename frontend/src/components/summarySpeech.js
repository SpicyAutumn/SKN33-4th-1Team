export function summaryToRead(result, sections) {
  if (!['answered', 'corrected_premise'].includes(result?.response_type)
    || typeof result.summary !== 'string' || !result.summary.trim()) return null;
  return sections.find((section) => section.text === result.summary)?.kind ?? null;
}

// Inject the browser API so cancellation and errors can be tested without audio.
export function createSummarySpeech({ synth, Utterance, update, schedule = setTimeout, unschedule = clearTimeout }) {
  let current = null;
  let timer;
  const stop = () => {
    unschedule(timer);
    if (current) { current = null; synth.cancel(); }
    update({ playing: false, message: '' });
  };
  const play = (text) => {
    stop();
    if (!synth || !Utterance) { update({ playing: false, message: '이 브라우저에서는 음성 읽기를 지원하지 않습니다.' }); return; }
    const voices = synth.getVoices().filter((voice) => /^ko(?:[-_]|$)/i.test(voice.lang));
    const voice = voices.find((item) => item.localService) || voices[0];
    if (!voice) { update({ playing: false, message: '한국어 음성이 준비되지 않았습니다. 기기의 한국어 음성 설정을 확인한 뒤 다시 눌러 주세요.' }); return; }
    const utterance = new Utterance(text);
    current = utterance;
    utterance.lang = 'ko-KR'; utterance.voice = voice; utterance.rate = 1;
    const finish = (message = '') => {
      if (current !== utterance) return;
      current = null; unschedule(timer); update({ playing: false, message });
    };
    utterance.onstart = () => { if (current === utterance) unschedule(timer); };
    utterance.onend = () => finish();
    utterance.onerror = () => finish('음성을 재생하지 못했습니다. 기기의 음성·소리 설정을 확인해 주세요.');
    update({ playing: true, message: '' });
    timer = schedule(() => {
      if (current !== utterance) return;
      finish('음성 재생을 시작하지 못했습니다. 다시 시도해 주세요.');
      synth.cancel();
    }, 10000);
    try { synth.cancel(); synth.speak(utterance); }
    catch { finish('음성을 재생하지 못했습니다. 다시 시도해 주세요.'); }
  };
  return { play, stop };
}
