"""Supabase-first AI route contracts.

Phase 1 ships schema/configuration only. Routes fail closed until a Supabase
project and the runtime PostgREST adapter are connected; no Mongo fallback is
allowed for private AI data.
"""

from fastapi import APIRouter, Depends, status

from lib.ai_provider import get_suggestion_provider
from lib.auth import AuthenticatedUser, auth_is_configured, require_user
from lib.supabase_config import require_supabase_runtime, supabase_is_configured
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
    AIStatus,
    AIUsageEvent,
    AIWritingSession,
    AIWritingSessionCreate,
)

router = APIRouter(prefix="/ai", tags=["ai"])


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
        message=(
            "Supabase is configured; the Phase 1 runtime adapter remains disabled."
            if configured
            else "Supabase migration and RLS are ready; connect project credentials to enable AI routes."
        ),
    )


@router.get("/profile", response_model=AIProfile)
async def get_profile(_user: AuthenticatedUser = Depends(require_user)) -> AIProfile:
    require_supabase_runtime()


@router.put("/profile", response_model=AIProfile)
async def update_profile(_payload: AIProfileUpdate, _user: AuthenticatedUser = Depends(require_user)) -> AIProfile:
    require_supabase_runtime()


@router.get("/onboarding", response_model=list[AIOnboardingAnswer])
async def list_onboarding(_user: AuthenticatedUser = Depends(require_user)) -> list[AIOnboardingAnswer]:
    require_supabase_runtime()


@router.put("/onboarding", response_model=AIOnboardingAnswer)
async def upsert_onboarding(_payload: AIOnboardingAnswerUpsert, _user: AuthenticatedUser = Depends(require_user)) -> AIOnboardingAnswer:
    require_supabase_runtime()


@router.get("/memories", response_model=list[AIMemory])
async def list_memories(_user: AuthenticatedUser = Depends(require_user)) -> list[AIMemory]:
    require_supabase_runtime()


@router.post("/memories", response_model=AIMemory, status_code=status.HTTP_201_CREATED)
async def create_memory(_payload: AIMemoryCreate, _user: AuthenticatedUser = Depends(require_user)) -> AIMemory:
    require_supabase_runtime()


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(_memory_id: str, _user: AuthenticatedUser = Depends(require_user)) -> None:
    require_supabase_runtime()


@router.post("/writing-sessions", response_model=AIWritingSession, status_code=status.HTTP_201_CREATED)
async def save_writing_session(_payload: AIWritingSessionCreate, _user: AuthenticatedUser = Depends(require_user)) -> AIWritingSession:
    require_supabase_runtime()


@router.post("/suggestion", response_model=AISuggestion)
async def create_suggestion(_payload: AISuggestionRequest, _user: AuthenticatedUser = Depends(require_user)) -> AISuggestion:
    require_supabase_runtime()


@router.post("/feedback", response_model=AIFeedback, status_code=status.HTTP_201_CREATED)
async def create_feedback(_payload: AISuggestionFeedbackCreate, _user: AuthenticatedUser = Depends(require_user)) -> AIFeedback:
    require_supabase_runtime()


@router.get("/usage", response_model=list[AIUsageEvent])
async def list_usage(_user: AuthenticatedUser = Depends(require_user)) -> list[AIUsageEvent]:
    require_supabase_runtime()