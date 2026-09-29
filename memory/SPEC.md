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

There is currently no account/auth system, Supabase/Postgres, Stripe, remote
document storage, or AI provider in the upstream project. The existing popup,
word counter, sessions, progress, and basic prompts are intentionally not
changed in Phase 1.

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

The upstream app has no auth to reuse. `AI_AUTH_MODE=supabase` is configured,
but AI routes fail closed until Supabase project values exist. FastAPI's auth
boundary is prepared to verify Supabase JWTs with the project's JWKS endpoint.
Paid access will come from `ai_entitlements`, never the extension's demo plan.

`AI_PROVIDER=mock` and `AI_MODEL=gpt-5.4-mini` are configuration defaults.
The mock provider is deterministic and validates the same structured response
contract a future OpenAI-compatible provider must satisfy. No provider key is
stored in or exposed to the extension.

## Key flows

1. The existing extension runs locally and offline exactly as before.
2. A future Supabase-authenticated client can upsert a profile and onboarding answers.
3. A future document processor creates metadata, then stores extracted chunks.
4. Users explicitly choose whether a completed writing session becomes AI
   memory; keystrokes are never automatically persisted as AI memory.
5. Suggestion requests retrieve only the requesting user's highest-overlap
   memories/chunks, call the configured provider, validate the structured
   result, save a suggestion, and record usage.
6. Feedback is scoped to an owned suggestion and changes its status only.

## Known intentional limits

- **MOCKED:** the AI provider is a deterministic local fallback; no external
  model or embeddings call is enabled in this phase.
- The migration creates the protected Storage bucket and metadata schema, but
  upload/processors are not enabled until project credentials are connected.
- Supabase Auth, entitlement lookups, and PostgREST runtime calls remain
  fail-closed because the user chose migration/configuration only for Phase 1.