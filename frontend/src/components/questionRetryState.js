import { clarificationFollowup } from '../clarificationFollowup.js';

export const createRetryDraft = (question) => ({ value: question, followup: null, selected: null });

export function retryDraftReducer(state, action) {
  if (action.type === 'edit') {
    // Free editing starts a new question; never pin a previous person's source.
    return createRetryDraft(action.value);
  }
  if (action.type === 'select') {
    const { question, result, option } = action;
    if (result.clarification?.reason_code === 'compound_question') {
      return createRetryDraft(option.label);
    }
    const followup = clarificationFollowup(question, result, option);
    return { value: followup.question,
      followup: followup.interaction_id ? followup : null,
      selected: option.id || option.label };
  }
  return state;
}

export function retryRequest(draft) {
  const question = draft.value.trim();
  if (!question || question.length > 1000) return null;
  return draft.followup ? { ...draft.followup, question } : question;
}
