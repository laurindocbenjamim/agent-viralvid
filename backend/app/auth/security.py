# -*- coding: utf-8 -*-
"""Auth bounded context: JWT token encoding and HttpOnly cookie dependency."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import html
from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def create_access_token(data: dict) -> str:
    """Encode a signed JWT with an expiry claim.

    Args:
        data (dict): Payload claims to embed in the token.

    Returns:
        str: Signed JWT string.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_session_from_cookie(
    access_token: Optional[str] = Cookie(default=None),
) -> str:
    """FastAPI dependency: extract and validate the session from an HttpOnly cookie.

    Args:
        access_token (Optional[str]): Cookie value injected by FastAPI.

    Returns:
        str: Validated session subject (token sub claim).

    Raises:
        HTTPException: 401 if the cookie is missing or the token is invalid.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session cookie.",
        )
    try:
        payload = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub: Optional[str] = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )
        return html.escape(sub)
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is invalid or expired.",
        )
