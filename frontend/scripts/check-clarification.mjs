import assert from 'node:assert/strict';
import { clarificationFollowup } from '../src/clarificationFollowup.js';

const followup = clarificationFollowup(
  '이순신 장군',
  {
    interaction_id: 'INT-1',
    message: '어느 인물을 말씀하시나요?',
    clarification: { question: '같은 이름의 인물이 여러 명입니다.' },
  },
  {
    label: '이순신 — 조선시대 선무공신 3등에 책록된 공신. 무신.',
    source_chunk_ids: ['aks:E0044901:hash:definition:0001'],
  },
);

assert.equal(followup.interaction_id, 'INT-1');
assert.equal(followup.clarification_context.original_question, '이순신 장군');
assert.equal(followup.clarification_context.clarification_turn_count, 1);
assert.deepEqual(followup.selected_source_chunk_ids, ['aks:E0044901:hash:definition:0001']);
assert.match(followup.question, /^이순신 — 조선시대 선무공신/);
assert.doesNotMatch(followup.question, /^이순신 장군 \(/);
console.log('PASS: clarification selection preserves context and removes the ambiguous original prefix');
