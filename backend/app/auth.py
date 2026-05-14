"""
Bearer-token auth for the RBI CMS API.

The mock RBI exposes a single token in env var RBI_API_KEY. Banks that
integrate with the mock present this in `Authorization: Bearer <token>`.

The UI calls these same endpoints from the browser; nginx adds the token
on its behalf via a forward header (see nginx.conf).
"""
from fastapi import Header, HTTPException, status

from app.config import settings


async def require_api_key(authorization: str | None = Header(default=None)) -> str:
    """
    Returns the caller's identity (the literal token, used as actor in audit).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header (expected 'Bearer <token>').",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.RBI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return "api_caller"
