"""RLS-backed Supabase document metadata and chunk routes."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from lib.auth import AuthenticatedUser, require_user
from lib.supabase_client import SupabaseAPIError, raise_http, user_rest
from models.ai import AIDocument, AIDocumentChunk, AIDocumentChunkCreate, AIDocumentUpload

router = APIRouter(prefix="/documents", tags=["documents"])


async def _owned_documents(user: AuthenticatedUser, extra: dict[str, str] | None = None) -> list[dict]:
    try:
        return await user_rest(
            "GET", "ai_documents", user.access_token,
            params={"select": "*", "user_id": f"eq.{user.id}", **(extra or {})},
        )
    except SupabaseAPIError as error:
        raise_http(error)


@router.get("", response_model=list[AIDocument])
async def list_documents(user: AuthenticatedUser = Depends(require_user)) -> list[AIDocument]:
    rows = await _owned_documents(user, {"order": "updated_at.desc", "limit": "200"})
    return [AIDocument(**row) for row in rows]


@router.post("/upload", response_model=AIDocument, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(payload: AIDocumentUpload, user: AuthenticatedUser = Depends(require_user)) -> AIDocument:
    safe_filename = Path(payload.filename).name
    storage_path = f"{user.id}/{uuid4()}/{safe_filename}"
    try:
        rows = await user_rest(
            "POST", "ai_documents", user.access_token,
            json={"user_id": user.id, **payload.model_dump(), "filename": safe_filename, "storage_path": storage_path},
            prefer="return=representation",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIDocument(**rows[0])


@router.get("/status/{document_id}", response_model=AIDocument)
async def document_status(document_id: str, user: AuthenticatedUser = Depends(require_user)) -> AIDocument:
    rows = await _owned_documents(user, {"id": f"eq.{document_id}", "limit": "1"})
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return AIDocument(**rows[0])


@router.post("/{document_id}/chunks", response_model=AIDocumentChunk, status_code=status.HTTP_201_CREATED)
async def add_document_chunk(document_id: str, payload: AIDocumentChunkCreate, user: AuthenticatedUser = Depends(require_user)) -> AIDocumentChunk:
    if not await _owned_documents(user, {"id": f"eq.{document_id}", "limit": "1"}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        rows = await user_rest(
            "POST", "ai_document_chunks", user.access_token,
            json={"user_id": user.id, "document_id": document_id, **payload.model_dump()},
            prefer="return=representation",
        )
        await user_rest(
            "PATCH", "ai_documents", user.access_token,
            params={"id": f"eq.{document_id}", "user_id": f"eq.{user.id}"},
            json={"processing_status": "ready"}, prefer="return=minimal",
        )
    except SupabaseAPIError as error:
        raise_http(error)
    return AIDocumentChunk(**rows[0])