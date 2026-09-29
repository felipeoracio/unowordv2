# Uno Word — PRD

## Source
- Repo cloned from https://github.com/felipeoracio/unowordv2.git into `/app` on 2026-09-29.
- Mongo removed (per user instruction). Persistence is Supabase Postgres (RLS + pgvector) + Supabase Auth + Supabase Storage (`ai-documents`).

## Stack
- Backend: FastAPI (uvicorn), async httpx, pyjwt, openai==1.99.9. Runs on `0.0.0.0:8001` under supervisor.
- Frontend: Vite + React 19 + TS + Tailwind v4 + shadcn (Base UI). Runs on `:3000` via `yarn start` (aliased to `vite`) under supervisor.
- DB: Supabase project `jvcbpnmtnjhftpukgppw` (pooler URL configured, migrations current: foundation + writing-session idempotency + document-processing-errors + `20260929040000_rag_match_user_chunks`).

## Phase 11 — RAG / Personalized Context (implemented 2026-09-29)
- New migration `20260929040000_rag_match_user_chunks.sql`:
  - Added `embedding_model` / `embedding_version` columns to `ai_document_chunks`, `ai_writing_chunks`, `ai_memories`.
  - Added `public.match_user_chunks(uuid, vector(1536), float, int)` — `security definer`, unions the 3 sources, enforces `user_id` predicate inside SQL so it works with the service-role key without cross-user leakage.
- `backend/lib/embeddings.py`: async OpenAI embeddings service (`text-embedding-3-small`, 1536-dim, provenance stamped).
- `backend/lib/retrieval.py`: embeds the query, calls `match_user_chunks` via service-role REST, dedupes by parent, returns typed chunks. Retrieved text is delimited and instructed as untrusted context.
- `backend/lib/ai_provider.py`: OpenAI Responses/Chat structured-outputs provider (JSON schema for `title` / `suggestion` / `why` / `related_topics[]`) + Mock provider for the Phase-13 fallback.
- `routers/ai.py`:
  - `/api/ai/memories POST` embeds on ingest.
  - `/api/ai/writing-sessions POST` embeds each chunk on ingest.
  - `/api/ai/suggestion POST`: auth → entitlement + daily-limit check → retrieve → compose (Phase-12 system prompt) → OpenAI structured output → persist `ai_suggestions` with `source_ids` from retrieval → write `ai_usage` row (`suggestion` or `suggestion_fallback`). Any provider/embedding failure falls back silently to the mock provider (Phase-13 basic prompt).
  - `/api/ai/status` reports `retrieval_ready` based on both Supabase and OPENAI_API_KEY presence.
  - `/api/ai/usage GET` returns per-user usage.
- `routers/documents.py`: document chunks embedded on upload.
- `backend/scripts/backfill_embeddings.py`: one-shot backfill for pre-Phase-11 rows in `ai_document_chunks`, `ai_writing_chunks`, `ai_memories`.

## Verification
- `python -c "import server"` — OK.
- `yarn typecheck` — OK.
- `/api/` returns 200. `/api/ai/status` reports `provider=openai`, `retrieval_ready=true`.
- `/api/ai/suggestion` end-to-end with a Pro-entitled test user: memory persisted, retrieval executed, OpenAI call attempted, response persisted with `source_ids`, usage row written.
- **BLOCKER**: the provided `OPENAI_API_KEY` returns HTTP 429 `credit_balance_exhausted` for both `text-embedding-3-small` and `gpt-5.4-mini`, so retrieval silently returns empty and the suggestion currently comes from the mock fallback path. Add credits at platform.openai.com/settings/organization/billing/ or switch to the Emergent Universal LLM key to enable real embeddings + suggestions.

## Users / auth
- Two Pro-entitled Supabase Auth users seeded via `scripts/seed_supabase_test_users.py`. Credentials in `/app/memory/test_credentials.md`.

## Deferred (per user's plan, out of scope for Phase 11)
- Document Preview UI, Memory Review UI (Phases 17-18).
- OCR / image ingestion (Phase 16).
- Feedback UI wiring (Phase 7).
- New onboarding UI (Phase 17).
- Un-mocking anything outside the suggestion + embeddings path.

## Env keys (all in backend/.env)
`CORS_ORIGINS`, `AI_AUTH_MODE=supabase`, `AI_PROVIDER=openai`, `AI_MODEL=gpt-5.4-mini`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBED_MODEL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_DB_URL`, `SUPABASE_JWT_AUDIENCE`, `OPENAI_API_KEY`, `AI_REQUIRE_SUBSCRIPTION`, optional `AI_DAILY_REQUEST_LIMIT`.
