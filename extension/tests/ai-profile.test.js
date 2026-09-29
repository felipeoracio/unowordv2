/** Tests for the local-only AI profile draft helpers. */
const assert = require('node:assert/strict');
const P = require('../shared/ai-profile.js');

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

test('createDraft returns a local-only empty profile', () => {
  const draft = P.createDraft();
  assert.equal(draft.syncStatus, 'local_only');
  assert.equal(draft.onboardingCompleted, false);
  assert.equal(P.hasPersonalization(draft), false);
});

test('sanitizeDraft trims user text and preserves completion', () => {
  const draft = P.sanitizeDraft({ writingGoal: '  Finish my memoir  ', onboardingCompleted: true }, 123);
  assert.equal(draft.writingGoal, 'Finish my memoir');
  assert.equal(draft.onboardingCompleted, true);
  assert.equal(draft.updatedAt, 123);
});

test('sanitizeDraft never accepts a remote sync status', () => {
  const draft = P.sanitizeDraft({ syncStatus: 'synced' });
  assert.equal(draft.syncStatus, 'local_only');
});

test('sanitizeDraft refreshes updatedAt after an explicit local edit', () => {
  const draft = P.sanitizeDraft({ updatedAt: 100, audience: 'Readers' }, 200);
  assert.equal(draft.updatedAt, 200);
});

test('sanitizeDraft safely handles invalid input', () => {
  assert.deepEqual(P.sanitizeDraft(null), P.createDraft());
  assert.deepEqual(P.sanitizeDraft('bad'), P.createDraft());
});

test('splitList supports commas and new lines', () => {
  assert.deepEqual(P.splitList('Memoir, Family stories\nTravel notes'), ['Memoir', 'Family stories', 'Travel notes']);
});

test('hasPersonalization recognizes any supplied field', () => {
  assert.equal(P.hasPersonalization({ audience: 'My family' }), true);
  assert.equal(P.hasPersonalization({ avoidTopics: 'Politics' }), true);
});

test('toApiProfile maps the draft to backend field names', () => {
  const mapped = P.toApiProfile({
    writingGoal: 'Write a memoir',
    audience: 'My children',
    currentProjects: 'Childhood, First job',
    avoidTopics: 'Medical details',
  });
  assert.equal(mapped.writing_goal, 'Write a memoir');
  assert.equal(mapped.audience, 'My children');
  assert.deepEqual(mapped.current_projects, ['Childhood', 'First job']);
  assert.deepEqual(mapped.avoid_topics, ['Medical details']);
  assert.equal(mapped.ai_preferences.sync_status, 'local_only');
});

test('cleanText enforces configured limits', () => {
  assert.equal(P.cleanText('abcdef', 3), 'abc');
});

(async () => {
  let passed = 0, failed = 0;
  for (const [name, fn] of tests) {
    try { await fn(); console.log('  \u2713', name); passed++; }
    catch (e) { console.log('  \u2717', name); console.log('     ', e.message); failed++; }
  }
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
})();