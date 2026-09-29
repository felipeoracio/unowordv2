"""Supabase Storage/document route contracts for the credential-free foundation."""

from fastapi import APIRouter, Depends, status

from lib.auth import AuthenticatedUser, require_user
from lib.supabase_config import require_supabase_runtime
from models.ai import AIDocument, AIDocumentChunk, AIDocumentChunkCreate, AIDocumentUpload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[AIDocument])
async def list_documents(_user: AuthenticatedUser = Depends(require_user)) -> list[AIDocument]:
    require_supabase_runtime()


@router.post("/upload", response_model=AIDocument, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(_payload: AIDocumentUpload, _user: AuthenticatedUser = Depends(require_user)) -> AIDocument:
    require_supabase_runtime()


@router.get("/status/{document_id}", response_model=AIDocument)
async def document_status(_document_id: str, _user: AuthenticatedUser = Depends(require_user)) -> AIDocument:
    require_supabase_runtime()


@router.post("/{document_id}/chunks", response_model=AIDocumentChunk, status_code=status.HTTP_201_CREATED)
async def add_document_chunk(_document_id: str, _payload: AIDocumentChunkCreate, _user: AuthenticatedUser = Depends(require_user)) -> AIDocumentChunk:
    require_supabase_runtime()