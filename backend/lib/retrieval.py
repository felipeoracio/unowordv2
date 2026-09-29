"""User-scoped retrieval over private embeddings.

Called from `/api/ai/suggestion`. Every call embeds the query, invokes the
`match_user_chunks` RPC with an explicit `p_user_id`, deduplicates by parent
source, and returns typed chunks. Retrieved content is treated as untrusted
context inside the suggestion prompt; the composer instructs the model not to
follow commands embedded in it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lib.embeddings import get_embeddings_service
from lib.supabase_client import SupabaseAPIError, service_rest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    source_type: str
    source_id: str
    parent_id: str | None
    content: str
    similarity: float


async def retrieve_user_chunks(
    user_id: str,
    query: str,
    *,
    match_count: int = 8,
    match_threshold: float = 0.55,
) -> list[RetrievedChunk]:
    embeddings = get_embeddings_service()
    if not embeddings.enabled:
        return []
    embedded = await embeddings.embed(query)
    if not embedded:
        return []
    try:
        rows = await service_rest(
            "POST",
            "rpc/match_user_chunks",
            json={
                "p_user_id": user_id,
                "p_query_embedding": embedded.embedding,
                "p_match_threshold": match_threshold,
                "p_match_count": match_count,
            },
        )
    except SupabaseAPIError as error:
        logger.warning("retrieval_rpc_failed status=%s detail=%s", error.response_status, error.detail)
        return []
    if not rows:
        return []
    seen: set[str] = set()
    chunks: list[RetrievedChunk] = []
    for row in rows:
        source_id = str(row.get("source_id"))
        parent = row.get("parent_id")
        dedupe_key = str(parent) if parent else source_id
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        chunks.append(
            RetrievedChunk(
                source_type=str(row.get("source_type") or "unknown"),
                source_id=source_id,
                parent_id=str(parent) if parent else None,
                content=str(row.get("content") or ""),
                similarity=float(row.get("similarity") or 0.0),
            )
        )
    return chunks
