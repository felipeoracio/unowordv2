"""Authentication boundary for AI routes.

The upstream UnoWord extension currently has no account system: plan state is a
local demo setting in chrome.storage. AI routes therefore fail closed until a
real trusted auth adapter is configured. A development header adapter exists
for local integration tests only and is disabled by default.
"""

import asyncio
import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from lib.supabase_config import get_supabase_config


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    plan: str
    access_token: str


def auth_is_configured() -> bool:
    config = get_supabase_config()
    return os.environ.get("AI_AUTH_MODE", "supabase").lower() == "supabase" and config.configured


def _verify_supabase_token(token: str) -> dict:
    config = get_supabase_config()
    signing_key = PyJWKClient(config.jwks_url, cache_keys=True).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=config.jwt_audience,
        issuer=config.issuer,
    )


async def require_user(
    authorization: str | None = Header(default=None),
    x_uno_user_id: str | None = Header(default=None),
) -> AuthenticatedUser:
    mode = os.environ.get("AI_AUTH_MODE", "supabase").lower()
    if mode == "supabase":
        if not auth_is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth is not configured for this deployment",
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = await asyncio.to_thread(_verify_supabase_token, token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase access token") from exc
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase access token")
        # Entitlement is intentionally unresolved until the Supabase runtime
        # adapter can read ai_entitlements server-side.
        return AuthenticatedUser(id=str(user_id), plan="unverified", access_token=token)

    if mode == "development_header" and os.environ.get("AI_DEV_AUTH_ENABLED", "false").lower() == "true":
        if not x_uno_user_id or len(x_uno_user_id) > 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        # The plan is server-configured in this adapter, never accepted from the client.
        plan = os.environ.get("AI_DEV_PLAN", "free")
        return AuthenticatedUser(id=x_uno_user_id, plan=plan, access_token="")

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI authentication is not configured for this deployment",
    )


def require_subscription(user: AuthenticatedUser) -> None:
    if os.environ.get("AI_REQUIRE_SUBSCRIPTION", "true").lower() == "true" and user.plan not in {"pro", "premium"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An eligible UnoWord plan is required")