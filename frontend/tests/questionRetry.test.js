import test from 'node:test';
import assert from 'node:assert/strict';
import { createRetryDraft, retryDraftReducer, retryRequest } from '../src/components/questionRetryState.js';
import { levelChangeRequest } from '../src/clarificationFollowup.js';

const result = { interaction_id: 'INT-1', clarification: { reason_code: 'ambiguous_entity', question: '어느 인물인가요?' } };
const first = { id: 'first', label: '충무공 이순신', source_chunk_ids: ['chunk-1'] };
const second = { id: 'second', label: '선무공신 이순신', source_chunk_ids: ['chunk-2'] };
const select = (state, option, response = result) => retryDraftReducer(state, { type: 'select', question: '이순신 장군', result: response, option });

test('option selection retains original interaction and exact selected sources', () => {
  const payload = retryRequest(select(createRetryDraft('이순신 장군'), second));
  assert.equal(payload.question, '선무공신 이순신에 대해 자세히 알려주세요.');
  assert.equal(payload.interaction_id, 'INT-1');
  assert.equal(payload.clarification_context.original_question, '이순신 장군');
  assert.equal(payload.clarification_context.clarification_response, second.label);
  assert.deepEqual(payload.selected_source_chunk_ids, ['chunk-2']);
});

test('changing the selected person replaces rather than accumulates sources', () => {
  const draft = select(select(createRetryDraft('이순신 장군'), first), second);
  assert.deepEqual(retryRequest(draft).selected_source_chunk_ids, ['chunk-2']);
});

test('manual edit clears the old person even if the original text is restored', () => {
  const selected = select(createRetryDraft('이순신 장군'), second);
  let draft = retryDraftReducer(selected, { type: 'edit', value: '경복궁은 어디에 있나요?' });
  assert.equal(retryRequest(draft), '경복궁은 어디에 있나요?');
  draft = retryDraftReducer(draft, { type: 'edit', value: selected.value });
  assert.equal(typeof retryRequest(draft), 'string');
  assert.equal(draft.selected, null);
});

test('compound question option remains a standalone question', () => {
  const response = { ...result, clarification: { reason_code: 'compound_question' } };
  const draft = select(createRetryDraft('질문 두 개'), { ...second, label: '거북선은 왜 만들었나요?' }, response);
  assert.equal(retryRequest(draft), '거북선은 왜 만들었나요?');
});

test('legacy answer without an interaction does not send orphaned source IDs', () => {
  const draft = select(createRetryDraft('이순신 장군'), second, { clarification: result.clarification });
  assert.equal(typeof retryRequest(draft), 'string');
});

test('normal editing and invalid length do not send a followup', () => {
  assert.equal(retryRequest(createRetryDraft('  새 질문  ')), '새 질문');
  assert.equal(retryRequest(createRetryDraft('  ')), null);
  assert.equal(retryRequest(createRetryDraft('가'.repeat(1001))), null);
});

test('answer level change keeps the selected person and exact source IDs', () => {
  const selected = retryRequest(select(createRetryDraft('이순신'), first));
  const next = levelChangeRequest(selected, selected.question);
  assert.equal(next.interaction_id, 'INT-1');
  assert.deepEqual(next.selected_source_chunk_ids, ['chunk-1']);
  assert.equal(next.clarification_context.original_question, '이순신 장군');
});

test('answer level change does not reuse a selection for another displayed question', () => {
  const selected = retryRequest(select(createRetryDraft('이순신'), first));
  assert.equal(levelChangeRequest(selected, '경복궁'), '경복궁');
});
