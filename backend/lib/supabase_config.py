"""Supabase configuration state for the credential-free Phase 1 foundation."""

import os
from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    anon_key: str
    service_role_key: str
    jwt_audience: str

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon_key)

    @property
    def jwks_url(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1/.well-known/jwks.json" if self.url else ""

    @property
    def issuer(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1" if self.url else ""


def get_supabase_config() -> SupabaseConfig:
    return SupabaseConfig(
        url=os.environ.get("SUPABASE_URL", "").strip(),
        anon_key=os.environ.get("SUPABASE_ANON_KEY", "").strip(),
        service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        jwt_audience=os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated").strip(),
    )


def supabase_is_configured() -> bool:
    return get_supabase_config().configured


def require_supabase_runtime() -> None:
    if not supabase_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase migration is ready, but project credentials are not configured",
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Supabase credentials are present, but the Phase 1 runtime adapter has not been enabled",
    )