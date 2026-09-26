export const reportTypes = [['incorrect_fact', '사실이 틀림'], ['citation_mismatch', '출처가 맞지 않음'], ['incomplete_answer', '설명이 부족함'], ['inappropriate_content', '부적절한 내용'], ['other', '기타']];
const length = (text) => Array.from(text).length;

export function reportPayload({ recordId, categories, content, quotes, answer, mode }) {
  const text = content.trim();
  if (!recordId) throw new Error('저장된 답변에서 제보해 주세요.');
  const allowedTypes = reportTypes;
  if (!categories.length || categories.some((value) => !allowedTypes.some(([code]) => code === value))) throw new Error('오류 유형을 선택해 주세요.');
  if (mode !== 'v2') {
    if (categories.length !== 1 || length(text) < 10 || length(text) > 2000) throw new Error('오류 유형 1개와 10~2,000자의 설명을 입력해 주세요.');
    return { search_record_id: recordId, category: categories[0], content: text };
  }
  if (quotes.length > 5 || quotes.some((quote) => !quote.text.trim() || length(quote.text) > 2000 || !Number.isInteger(quote.start_offset) || !Number.isInteger(quote.end_offset) || quote.start_offset < 0 || quote.end_offset <= quote.start_offset || quote.end_offset > length(answer) || Array.from(answer).slice(quote.start_offset, quote.end_offset).join('') !== quote.text)) throw new Error('답변 본문에서 최대 5개의 문구를 선택해 주세요.');
  if (length(text) > 2000 || ((!quotes.length || categories.includes('other')) && length(text) < 10)) throw new Error('선택 문구가 없거나 기타 유형이면 10자 이상의 설명이 필요합니다.');
  return { search_record_id: recordId, categories, content: text, selected_quotes: quotes };
}
