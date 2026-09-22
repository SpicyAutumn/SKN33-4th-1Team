import test from 'node:test';
import assert from 'node:assert/strict';
import { displayParagraphs } from '../src/components/displayParagraphs.js';

const sample = '수원 화성은 경기도 수원시에 있는 조선후기 읍성으로, 1796년에 축성되었습니다. 정조대왕이 아버지 사도세자의 능을 화산으로 옮기고 수원부를 팔달산 아래로 옮기면서 축조가 본격화되었습니다. 성벽은 돌로 쌓아 지형에 따라 4~6m 높이를 가지며, 위로 올라가면서 안으로 들어가는 규형 쌓기를 기본으로 합니다. 동서남북에 장안문, 팔달문, 청룡문, 화서문 등 4개의 성문이 있고, 적의 침입을 막기 위해 5개의 암문이 설치되어 있습니다. 또한 공심돈, 포루, 적대 등 다른 성곽에서는 보기 드문 새로운 방어 시설이 도입되었습니다. 화성은 자연 지세를 이용해 불규칙한 형태로 쌓아 올린 것이 특징이며, 성벽 중앙에는 정조가 머물렀던 행궁이 자리 잡고 있습니다.';
test('long unformatted answer is visually grouped without any text changes', () => {
  const parts = displayParagraphs(sample);
  assert.ok(parts.length > 1); assert.equal(parts.join(''), sample);
  assert.ok(parts.slice(0, -1).every(part => /[다요][.!?][ \t]+$/.test(part)));
});
test('existing paragraphs, lists, quotes, URLs and short answers remain intact', () => {
  for (const text of [sample + '\n다음 문단', sample + '\r\n- 목록', '짧은 답변입니다.', sample + ' “인용문입니다.”', sample + ' https://example.com/a.b']) {
    assert.deepEqual(displayParagraphs(text), [text]);
  }
});
test('decimal numbers, numbering and unicode remain intact', () => {
  const text = '🙂 1. 성벽 길이는 5.4km입니다. ' + sample;
  const parts = displayParagraphs(text);
  assert.equal(parts.join(''), text);
  assert.ok(parts.some(part => part.includes('5.4km')));
  assert.ok(parts[0].startsWith('🙂 1.'));
  let offset = 0;
  for (const part of parts) {
    assert.equal(Array.from(text).slice(offset, offset + Array.from(part).length).join(''), part);
    offset += Array.from(part).length;
  }
});
