export function clarificationFollowup(question, result, option) {
  const label = String(option?.label || "").trim();
  return {
    question: label ? `${label}에 대해 자세히 알려주세요.` : question,
    interaction_id: result?.interaction_id || undefined,
    selected_source_chunk_ids: Array.isArray(option?.source_chunk_ids) ? option.source_chunk_ids : [],
    clarification_context: {
      original_question: question,
      clarification_question: result?.clarification?.question || result?.message || "선택할 대상을 알려주세요.",
      clarification_response: label,
      clarification_turn_count: 1,
    },
  };
}
