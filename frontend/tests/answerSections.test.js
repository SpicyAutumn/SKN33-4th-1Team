import test from "node:test";
import assert from "node:assert/strict";
import { answerSections } from "../src/components/answerSections.js";

const corrected = (overrides = {}) => ({
  response_type: "corrected_premise",
  premise_correction: { corrected_premise: "2002년에 개관했습니다." },
  summary: "개관 연도는 2002년입니다.",
  message: "2001년이 아니라 2002년에 개관했습니다. 전시실은 두 곳입니다.",
  ...overrides,
});

test("correction, summary and full explanation preserve order and input", () => {
  const input = corrected();
  const before = structuredClone(input);
  assert.deepEqual(answerSections(input).map(({ text }) => text), [
    input.premise_correction.corrected_premise, input.summary, input.message,
  ]);
  assert.deepEqual(input, before);
});

test("all exact duplicate combinations are displayed once with priority", () => {
  for (const [detail, summary, message, expected] of [
    ["A", "A", "A", ["correction"]],
    ["A", "A", "B", ["correction", "message"]],
    ["A", "B", "A", ["correction", "summary"]],
    ["A", "B", "B", ["correction", "summary"]],
  ]) {
    const sections = answerSections(corrected({ premise_correction: { corrected_premise: detail }, summary, message }));
    assert.deepEqual(sections.map(({ kind }) => kind), expected);
  }
});

test("partial overlap, long content, newlines and whitespace are not rewritten", () => {
  const message = "2002년입니다.\n" + "추가 설명입니다. ".repeat(500);
  const sections = answerSections(corrected({ premise_correction: { corrected_premise: "2002년입니다." }, summary: " 2002년입니다. ", message }));
  assert.equal(sections.length, 3);
  assert.equal(sections[1].text, " 2002년입니다. ");
  assert.equal(sections[2].text, message);
});

test("missing or malformed correction and summary fall back to full explanation", () => {
  for (const value of [undefined, null, "", "  ", 42, [], {}]) {
    const sections = answerSections(corrected({ premise_correction: { corrected_premise: value }, summary: value }));
    assert.deepEqual(sections.map(({ kind }) => kind), ["message"]);
  }
  assert.deepEqual(answerSections(corrected({ premise_correction: null, summary: null })).map(({ kind }) => kind), ["message"]);
});

test("valid correction or summary survives a missing body", () => {
  assert.deepEqual(answerSections(corrected({ summary: null, message: null })).map(({ kind }) => kind), ["correction"]);
  assert.deepEqual(answerSections(corrected({ premise_correction: null, message: null })).map(({ kind }) => kind), ["summary"]);
});

test("ordinary answer hides stale correction fields and deduplicates summary", () => {
  assert.deepEqual(answerSections(corrected({ response_type: "answered", summary: "정상 답변", message: "정상 답변" })).map(({ kind }) => kind), ["summary"]);
});

test("non-answer responses show the final message rather than a stale summary", () => {
  for (const response_type of ["insufficient_evidence", "needs_clarification", "safety_refusal", "out_of_scope"]) {
    const sections = answerSections(corrected({ response_type, message: "확인할 근거가 부족합니다." }));
    assert.deepEqual(sections, [{ kind: "message", title: "전체 설명", text: "확인할 근거가 부족합니다." }]);
  }
});

test("no usable content produces an empty result for the UI fallback", () => {
  assert.deepEqual(answerSections(corrected({ premise_correction: {}, summary: " ", message: null })), []);
  assert.deepEqual(answerSections(), []);
});
