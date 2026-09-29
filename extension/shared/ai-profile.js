/**
 * UnoWord — local AI profile draft helpers.
 *
 * Phase 1 stores this draft in chrome.storage.local only. Nothing here sends
 * data over the network. The API mapper exists so a future explicit sync can
 * reuse the same shape after Supabase Auth is connected.
 */
(function attach(scope) {
  const TEXT_LIMITS = {
    writingGoal: 2000,
    audience: 500,
    currentProjects: 2000,
    avoidTopics: 1000,
    personalContext: 5000,
  };

  function cleanText(value, max) {
    return String(value == null ? '' : value).trim().slice(0, max);
  }

  function normalizeListInput(value, max) {
    const text = Array.isArray(value) ? value.join(', ') : value;
    return cleanText(text, max);
  }

  function sanitizeDraft(value = {}, updatedAt = null) {
    const source = value && typeof value === 'object' ? value : {};
    const storedUpdatedAt = Number(source.updatedAt);
    return {
      writingGoal: cleanText(source.writingGoal, TEXT_LIMITS.writingGoal),
      audience: cleanText(source.audience, TEXT_LIMITS.audience),
      currentProjects: normalizeListInput(source.currentProjects, TEXT_LIMITS.currentProjects),
      avoidTopics: normalizeListInput(source.avoidTopics, TEXT_LIMITS.avoidTopics),
      personalContext: cleanText(source.personalContext, TEXT_LIMITS.personalContext),
      onboardingCompleted: source.onboardingCompleted === true,
      syncStatus: 'local_only',
      updatedAt: Number.isFinite(updatedAt) && updatedAt > 0
        ? updatedAt
        : (Number.isFinite(storedUpdatedAt) && storedUpdatedAt > 0 ? storedUpdatedAt : null),
    };
  }

  function createDraft(overrides = {}) {
    return sanitizeDraft(overrides);
  }

  function splitList(value) {
    return normalizeListInput(value, 5000)
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 50);
  }

  function hasPersonalization(value) {
    const draft = sanitizeDraft(value);
    return Boolean(
      draft.writingGoal || draft.audience || draft.currentProjects ||
      draft.avoidTopics || draft.personalContext
    );
  }

  function toApiProfile(value) {
    const draft = sanitizeDraft(value);
    return {
      writing_goal: draft.writingGoal || null,
      writing_style: null,
      audience: draft.audience || null,
      primary_topics: [],
      current_projects: splitList(draft.currentProjects),
      favorite_subjects: [],
      avoid_topics: splitList(draft.avoidTopics),
      personal_context: draft.personalContext || null,
      ai_preferences: { source: 'extension_onboarding', sync_status: draft.syncStatus },
    };
  }

  const api = { TEXT_LIMITS, cleanText, sanitizeDraft, createDraft, splitList, hasPersonalization, toApiProfile };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  scope.WCAIProfile = api;
})(typeof self !== 'undefined' ? self : (typeof window !== 'undefined' ? window : this));