"""RLS-backed AI profile, memory, suggestion, feedback, and usage routes."""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from lib.ai_provider import get_suggestion_provider
from lib.ai_access import get_entitlement, require_ai_user
from lib.auth import AuthenticatedUser, auth_is_configured
from lib.chunking import chunk_text
from lib.dates import today_iso
from lib.supabase_client import SupabaseAPIError, raise_http, service_rest, user_rest
from lib.supabase_config import supabase_is_configured
from models.ai import (
    AIFeedback,
    AIMemory,
    AIMemoryCreate,
    AIOnboardingAnswer,
    AIOnboardingAnswerUpsert,
    AIProfile,
    AIProfileUpdate,
    AISuggestion,
    AISuggestionFeedbackCreate,
    AISuggestionRequest,
    AISuggestionResult,
    AIStatus,
    AIUsageEvent,
    AIWritingChunk,
    AIWritingSession,
    AIWritingSessionCreate,
)

router = APIRouter(prefix="/ai", tags=["ai"])


async def _user_rows(table: str, user: AuthenticatedUser, *, extra: dict[str, str] | None = None) -> list[dict]:
    params = {"select": "*", "user_id": f"eq.{user.id}", **(extra or {})}
    try:
        return await user_rest("GET", table, user.access_token, params=params)
    except SupabaseAPIError as error:
        raise_http(error)


async def _entitlement(user_id: str) -> dict:
    entitlement = await get_entitlement(user_id)
    if not entitlement:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An eligible UnoWord AI plan is required")
    return entitlement


async def _build_context(user: AuthenticatedUser, payload: AISuggestionRequest) -> tuple[str, list[str]]:
    profile = await _user_rows("ai_profiles", user, extra={"limit": "1"})
    answers = await _user_rows("ai_onboarding_answers", user, extra={"order": "updated_at.desc", "limit": "20"})
    memories = await _user_rows("ai_memories", user, extra={"order": "importance.desc,updated_at.desc", "limit": "30"})
    previous = await _user_rows("ai_suggestions", user, extra={"order": "created_at.desc", "limit": "15"})

    parts: list[str] = []
    source_ids: list[str] = []
    if payload.current_writing:
        parts.append(f"Current writing: {payload.current_writing}")
    if payload.current_project:
        parts.append(f"Current project: {payload.current_project}")
    if profile:
        item = profile[0]
        parts.append(
            "Profile: " + "; ".join(
                str(item.get(field)) for field in (
                    "writing_goal", "writing_style", "audience", "primary_topics",
                    "current_projects", "favorite_subjects", "avoid_topics", "personal_context",
                ) if item.get(field)
            )
        )
        source_ids.append(item["id"])
    for answer in answers:
        parts.append(f"Onboarding — {answer.get('question')}: {answer.get('answer')}")
        source_ids.append(answer["id"])
    for memory in memories:
        parts.append(f"Memory ({memory.get('memory_type')}): {memory.get('memory')}")
        source_ids.append(memory["id"])
    for suggestion in previous:
        parts.append(f"Previous suggestion ({suggestion.get('status')}): {suggestion.get('suggestion')}")
    return "\n".join(parts[:60]) or "No saved user context is available yet.", source_ids[:50]


@router.get("/status", response_model=AIStatus)
async def ai_status() -> AIStatus:
    provider = get_suggestion_provider()
    configured = supabase_is_configured()
    return AIStatus(
        auth_configured=auth_is_configured(),
        database="supabase",
        database_configured=configured,
        provider=provider.name,
        model=provider.model,
        retrieval_ready=configured,
        message="Supabase Auth, PostgREST, RLS, and pgvector are connected." if configured else "Supabase is not configured.",
    )


@router.get("/profile", response_model=AIProfile)
async def get_profile(user: AuthenticatedUser = Depends(require_ai_user)) -> AIProfile:
    rows = await _user_rows("ai_profiles", user, extra={"limit": "1"})
    if rows:
        return AIProfile(**rows[0])
    try:
        created = await user_rest(
            "POST", "ai_profiles", user.access_token,
            json={"user_id": user.id}, prefer="return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIProfile(**created[0])


@router.put("/profile", response_model=AIProfile)
async def update_profile(payload: AIProfileUpdate, user: AuthenticatedUser = Depends(require_ai_user)) -> AIProfile:
    body = {"user_id": user.id, **payload.model_dump()}
    try:
        rows = await user_rest(
            "POST", "ai_profiles", user.access_token,
            params={"on_conflict": "user_id"}, json=body,
            prefer="resolution=merge-duplicates,return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIProfile(**rows[0])


@router.get("/onboarding", response_model=list[AIOnboardingAnswer])
async def list_onboarding(user: AuthenticatedUser = Depends(require_ai_user)) -> list[AIOnboardingAnswer]:
    rows = await _user_rows("ai_onboarding_answers", user, extra={"order": "updated_at.desc", "limit": "100"})
    return [AIOnboardingAnswer(**row) for row in rows]


@router.put("/onboarding", response_model=AIOnboardingAnswer)
async def upsert_onboarding(payload: AIOnboardingAnswerUpsert, user: AuthenticatedUser = Depends(require_ai_user)) -> AIOnboardingAnswer:
    try:
        rows = await user_rest(
            "POST", "ai_onboarding_answers", user.access_token,
            params={"on_conflict": "user_id,question_id"},
            json={"user_id": user.id, **payload.model_dump()},
            prefer="resolution=merge-duplicates,return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIOnboardingAnswer(**rows[0])


@router.get("/memories", response_model=list[AIMemory])
async def list_memories(user: AuthenticatedUser = Depends(require_ai_user)) -> list[AIMemory]:
    rows = await _user_rows("ai_memories", user, extra={"order": "updated_at.desc", "limit": "200"})
    return [AIMemory(**row) for row in rows]


@router.post("/memories", response_model=AIMemory, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: AIMemoryCreate, user: AuthenticatedUser = Depends(require_ai_user)) -> AIMemory:
    try:
        rows = await user_rest(
            "POST", "ai_memories", user.access_token,
            json={"user_id": user.id, **payload.model_dump()}, prefer="return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIMemory(**rows[0])


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str, user: AuthenticatedUser = Depends(require_ai_user)) -> None:
    try:
        rows = await user_rest(
            "DELETE", "ai_memories", user.access_token,
            params={"id": f"eq.{memory_id}", "user_id": f"eq.{user.id}"},
            prefer="return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")


@router.post("/writing-sessions", response_model=AIWritingSession, status_code=status.HTTP_201_CREATED)
async def save_writing_session(payload: AIWritingSessionCreate, user: AuthenticatedUser = Depends(require_ai_user)) -> AIWritingSession:
    session: AIWritingSession | None = None
    if payload.existing_session_ref:
        existing = await _user_rows(
            "ai_writing_sessions",
            user,
            extra={"existing_session_ref": f"eq.{payload.existing_session_ref}", "limit": "1"},
        )
        if existing:
            session = AIWritingSession(**existing[0])
    try:
        if session is None:
            session_body = {**payload.model_dump(), "user_id": user.id}
            if not payload.save_to_memory:
                session_body["content"] = None
            sessions = await user_rest("POST", "ai_writing_sessions", user.access_token, json=session_body, prefer="return=representation")
            session = AIWritingSession(**sessions[0])
        if payload.save_to_memory and payload.content:
            chunks = [
                AIWritingChunk(user_id=user.id, writing_session_id=session.id, chunk_index=index, content=content).model_dump(mode="json")
                for index, content in enumerate(chunk_text(payload.content))
            ]
            await user_rest(
                "POST", "ai_writing_chunks", user.access_token,
                params={"on_conflict": "writing_session_id,chunk_index"},
                json=chunks,
                prefer="resolution=merge-duplicates,return=minimal",
            )
    except SupabaseAPIError as error:
        raise_http(error)
    return session


@router.post("/suggestion", response_model=AISuggestion)
async def create_suggestion(payload: AISuggestionRequest, user: AuthenticatedUser = Depends(require_ai_user)) -> AISuggestion:
    entitlement = await _entitlement(user.id)
    date_key = today_iso()
    daily_limit = int(entitlement.get("daily_request_limit") or os.environ.get("AI_DAILY_REQUEST_LIMIT", "0"))
    if daily_limit:
        try:
            used = await service_rest(
                "GET", "ai_usage",
                params={"select": "id", "user_id": f"eq.{user.id}", "date": f"eq.{date_key}", "request_type": "eq.suggestion"},
            )
        except SupabaseAPIError as error:
            raise_http(error)
        if len(used) >= daily_limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily AI suggestion limit reached")

    context, source_ids = await _build_context(user, payload)
    try:
        result: AISuggestionResult = await get_suggestion_provider().generate_suggestion(context)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from error
    try:
        rows = await user_rest(
            "POST", "ai_suggestions", user.access_token,
            json={
                "user_id": user.id,
                "title": result.title,
                "suggestion": result.suggestion,
                "reason": result.why,
                "context_summary": context[:2000],
                "related_topics": result.related_topics,
                "source_ids": source_ids,
                "status": "shown",
            },
            prefer="return=representation",
        )
        await service_rest(
            "POST", "ai_usage",
            json={"user_id": user.id, "date": date_key, "request_type": "suggestion"},
            prefer="return=minimal",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AISuggestion(**rows[0])


@router.post("/feedback", response_model=AIFeedback, status_code=status.HTTP_201_CREATED)
async def create_feedback(payload: AISuggestionFeedbackCreate, user: AuthenticatedUser = Depends(require_ai_user)) -> AIFeedback:
    owned = await _user_rows("ai_suggestions", user, extra={"id": f"eq.{payload.suggestion_id}", "limit": "1"})
    if not owned:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    try:
        rows = await user_rest(
            "POST", "ai_feedback", user.access_token,
            json={"user_id": user.id, **payload.model_dump()}, prefer="return=representation",
        )
        await user_rest(
            "PATCH", "ai_suggestions", user.access_token,
            params={"id": f"eq.{payload.suggestion_id}", "user_id": f"eq.{user.id}"},
            json={"status": "accepted" if payload.helpful else "rejected"}, prefer="return=minimal",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIFeedback(**rows[0])


@router.get("/usage", response_model=list[AIUsageEvent])
async def list_usage(user: AuthenticatedUser = Depends(require_ai_user)) -> list[AIUsageEvent]:
    rows = await _user_rows("ai_usage", user, extra={"order": "created_at.desc", "limit": "200"})
    return [AIUsageEvent(**row) for row in rows]