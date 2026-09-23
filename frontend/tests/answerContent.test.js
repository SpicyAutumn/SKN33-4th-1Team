import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { buildSync } from 'esbuild';

const require = createRequire(import.meta.url);
const compiled = buildSync({ entryPoints: ['src/components/AnswerContent.jsx'], bundle: true,
  write: false, platform: 'node', format: 'cjs', jsx: 'automatic',
  loader: { '.css': 'empty' }, external: ['react', 'react/jsx-runtime'] }).outputFiles[0].text;
const bundled = { exports: {} };
new Function('require', 'module', 'exports', compiled)(require, bundled, bundled.exports);
const AnswerContent = bundled.exports.default;

test('visual paragraph spans preserve the original message and report selection target', () => {
  const message = '수원 화성의 성벽은 자연 지형을 따라 이어지는 성곽이며 다양한 방어 시설을 갖추고 있습니다. '.repeat(9) + '🙂';
  const answerRef = { current: null };
  const result = { response_type: 'answered', message, summary: '기존 요약입니다.' };
  const tree = AnswerContent({ result, answerRef });
  const paragraphs = tree.props.children.map(section => section.props.children[1]);
  const target = paragraphs.find(paragraph => paragraph.props.ref === answerRef);
  assert.ok(target.props.children.length > 1);
  assert.ok(target.props.children.every(span => span.type === 'span'));
  assert.equal(target.props.children.map(span => span.props.children).join(''), message);
  assert.equal(paragraphs[0].props.children, result.summary);
  assert.equal(result.message, message);
});

test('report selection refers to the exact original message after every deduplication case', () => {
  const message = '🙂 근정전.\n근정전.';
  for (const [correction, summary] of [['정정', '요약'], [message, '요약'], ['정정', message], [message, message]]) {
    const answerRef = { current: null };
    const result = { response_type: 'corrected_premise', message, summary,
      premise_correction: { corrected_premise: correction } };
    const paragraphs = AnswerContent({ result, answerRef }).props.children.map(section => section.props.children[1]);
    const targets = paragraphs.filter(paragraph => paragraph.props.ref === answerRef);
    assert.equal(targets.length, 1);
    assert.equal(targets[0].type, 'p');
    assert.equal(targets[0].props.children, message);
  }
});

test('saved answers without a summary retain their full selectable message', () => {
  const answerRef = { current: null };
  const message = '저장된 전체 설명입니다.';
  const tree = AnswerContent({ result: { response_type: 'answered', savedRecord: true, message }, answerRef });
  assert.equal(tree.props.children.length, 1);
  assert.equal(tree.props.children[0].props.children[1].props.ref, answerRef);
});

test('missing message never makes a summary selectable as the original answer', () => {
  const answerRef = { current: null };
  const tree = AnswerContent({ result: { response_type: 'answered', summary: '요약만 있음' }, answerRef });
  assert.equal(tree.props.children[0].props.children[1].props.ref, undefined);
});
