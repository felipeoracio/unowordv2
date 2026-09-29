# UnoWord AI Writing Coach — Phase 1 Specification

## Current product baseline

The authoritative existing product is the public `felipeoracio/uno-word`
repository. It is a Manifest V3 Chrome extension with a vanilla HTML/CSS/JS
popup, `background.js` service worker, `content.js` input observer, and
`chrome.storage.local` as its only persistence layer. `shared/wordcount.js`
owns Unicode-aware typed/pasted word counting; `shared/history.js` owns local
history, streaks, CSV, and range aggregation; `shared/prompts.js` owns the
English/Spanish static prompt library. The local Pro toggle is a demo setting,
not server-authenticated billing.

The synchronized upstream baseline had no account/auth system, Supabase,
Stripe, remote document storage, or AI provider. This workspace now adds the
Supabase backend alongside that preserved extension; word counting, sessions,
progress, and basic prompts remain unchanged.

## Phase 1 backend foundation

The mounted Emergent workspace exposes FastAPI routes under `/api`, while all
new AI persistence is defined for Supabase Postgres. The migration at
`supabase/migrations/20260929010000_ai_writing_coach_foundation.sql` creates:

- `ai_profiles` and `ai_onboarding_answers`
- `ai_documents` and `ai_document_chunks`
- `ai_writing_sessions` and `ai_writing_chunks`
- `ai_memories`, `ai_suggestions`, `ai_feedback`, and `ai_usage`
- `ai_entitlements` for server-authoritative paid access

Every table has Row Level Security. Policies scope rows to `auth.uid()`, the
private `ai-documents` Storage bucket scopes object paths to the user's UUID,
and the `match_ai_context` RPC can retrieve only the caller's vector context.
Embedding columns use `vector(1536)` with partial HNSW cosine indexes.

## Authentication and provider behavior

`AI_AUTH_MODE=supabase` is live. `/api/auth/signup`, `/login`, `/refresh`,
`/me`, and `/logout` proxy Supabase Auth and keep browser tokens in secure,
httpOnly cookies. FastAPI verifies this project's legacy HS256 user tokens and
also supports JWKS after a future asymmetric signing-key rotation. Paid access
comes from `ai_entitlements`, never the extension's demo plan.

`AI_PROVIDER=mock` and `AI_MODEL=gpt-5.4-mini` are configuration defaults.
The mock provider is deterministic and validates the same structured response
contract a future OpenAI-compatible provider must satisfy. No provider key is
stored in or exposed to the extension.

## Key flows

1. The existing extension runs locally and offline exactly as before.
2. A Supabase-authenticated client can upsert a profile and onboarding answers.
3. Authenticated users can create protected document metadata and extracted
   chunks; binary parsers remain a separate future processor.
4. Users explicitly choose whether a completed writing session becomes AI
   memory; keystrokes are never automatically persisted as AI memory.
5. Suggestion requests retrieve only the requesting user's highest-overlap
   memories/chunks, call the configured provider, validate the structured
   result, save a suggestion, and record usage.
6. Feedback is scoped to an owned suggestion and changes its status only.

## Known intentional limits

- **MOCKED:** the AI provider is a deterministic local fallback; no external
  model or embeddings call is enabled in this phase.
- The private Storage bucket and document metadata/chunk schema are live, but
  binary upload/parsers and embeddings generation are not enabled yet.
- Supabase Auth verifies legacy HS256 access tokens with the project JWT secret
  (and supports JWKS for a future asymmetric-key rotation). FastAPI forwards
  the verified user token to PostgREST, so RLS remains authoritative; service-
  role calls are restricted to entitlement lookup and usage writes.

## Extension AI onboarding foundation

The verified GitHub extension source at commit `a4fb0ba` is synchronized into
`/app/extension`. Its existing Pro onboarding is now five steps: language,
word goal, themes, optional AI context, and completion. The optional context
captures a writing goal, audience, current projects, and topics to avoid.

The draft is sanitized by `extension/shared/ai-profile.js` and stored inside
`wc_settings.aiProfileDraft` with `syncStatus: "local_only"`. It is never sent
to the backend automatically. Skipping the step does not erase an existing
draft. `toApiProfile()` prepares the Supabase payload shape, but the current
extension still requires a future explicit sign-in/sync control before sending it.

## Verified Supabase isolation

Two confirmed test accounts with active Pro entitlements are documented in
`memory/test_credentials.md`. Public-ingress verification proved separate
profiles and memories, blocked cross-user memory deletion and document status
access, generated a suggestion, and recorded user-scoped usage through RLS.