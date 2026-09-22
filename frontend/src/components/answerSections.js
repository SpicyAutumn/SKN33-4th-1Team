const usableText = (value) => typeof value === "string" && value.trim().length > 0;

// Only remove exact duplicates. Preserve punctuation, whitespace and partial overlap.
export function answerSections(result = {}) {
  const { response_type: type, premise_correction: correction, summary, message } = result;
  const candidates = [];
  if (type === "corrected_premise") {
    candidates.push({ kind: "correction", title: "확인된 정정 내용", text: correction?.corrected_premise });
  }
  if (type === "answered" || type === "corrected_premise") {
    candidates.push({ kind: "summary", title: "핵심 요약", text: summary });
  }
  candidates.push({ kind: "message", title: "전체 설명", text: message });
  const seen = new Set();
  return candidates.filter(({ text }) => {
    if (!usableText(text) || seen.has(text)) return false;
    seen.add(text);
    return true;
  });
}
