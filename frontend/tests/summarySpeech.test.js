import test from 'node:test';
import assert from 'node:assert/strict';
import { createSummarySpeech, summaryToRead } from '../src/components/summarySpeech.js';
import { answerSections } from '../src/components/answerSections.js';

function setup(voices = [{ lang: 'ko-KR', localService: true }]) {
  const states = []; const spoken = []; let canceled = 0; let timeout;
  const synth = { getVoices: () => voices, cancel: () => { canceled++; }, speak: (item) => spoken.push(item) };
  const control = createSummarySpeech({ synth, Utterance: class { constructor(text) { this.text = text; } },
    update: (state) => states.push(state), schedule: (fn) => { timeout = fn; }, unschedule() {} });
  return { ...control, states, spoken, timeout: () => timeout(), canceled: () => canceled };
}
test('only an actual summary is spoken once, including a deduplicated correction', () => {
  const result = { response_type: 'corrected_premise', summary: '원문\n요약', message: '상세 본문', premise_correction: { corrected_premise: '원문\n요약' } };
  assert.equal(summaryToRead(result, answerSections(result)), 'correction');
  for (const response_type of ['needs_clarification', 'insufficient_evidence', 'safety_refusal']) {
    assert.equal(summaryToRead({ ...result, response_type }, answerSections(result)), null);
  }
  assert.equal(summaryToRead({ response_type: 'answered', message: '전체 설명만' }, []), null);
});
test('reads unchanged text with a Korean local voice and completes', () => {
  const local = { lang: 'ko-KR', localService: true };
  const c = setup([{ lang: 'en-US' }, { lang: 'ko-KR', localService: false }, local]);
  c.play('원문\n요약.'); assert.equal(c.spoken[0].text, '원문\n요약.');
  assert.equal(c.spoken[0].voice, local); c.spoken[0].onstart(); c.spoken[0].onend();
  assert.equal(c.states.at(-1).playing, false);
});
test('stopping cancels audio and ignores stale callbacks', () => {
  const c = setup(); c.play('처음'); const old = c.spoken[0]; c.stop();
  assert.ok(c.canceled() >= 2); c.play('다음'); old.onend(); old.onerror();
  assert.equal(c.states.at(-1).playing, true);
});
test('missing Korean voice does not speak; later available voice can retry', () => {
  const voices = []; const c = setup(voices); c.play('요약');
  assert.equal(c.spoken.length, 0); assert.match(c.states.at(-1).message, /한국어/);
  voices.push({ lang: 'ko-KR' }); c.play('요약'); assert.equal(c.spoken.length, 1);
});
test('unsupported browser gives an explanation', () => {
  let state; createSummarySpeech({ update: (value) => { state = value; } }).play('요약');
  assert.match(state.message, /지원하지/);
});
test('audio error and start timeout recover the button', () => {
  const c = setup(); c.play('요약'); c.spoken[0].onerror();
  assert.equal(c.states.at(-1).playing, false); assert.ok(c.states.at(-1).message);
  c.play('재시도'); c.timeout(); assert.equal(c.states.at(-1).playing, false);
  assert.match(c.states.at(-1).message, /시작하지/);
});
