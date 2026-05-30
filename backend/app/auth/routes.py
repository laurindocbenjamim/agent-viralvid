# -*- coding: utf-8 -*-
"""Auth routes: anonymous session token issuance via HttpOnly cookie."""

import uuid
from typing import Dict

from fastapi import APIRouter, Response

from backend.app.auth.security import create_access_token
from backend.app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/session")
async def create_session(response: Response) -> Dict[str, str]:
    """Issue a new anonymous session token stored in an HttpOnly cookie.

    Any client (browser or API consumer) can call this endpoint to obtain a
    secure session token. No credentials are required. The token is signed and
    validated on every subsequent request via the cookie dependency.

    Args:
        response (Response): FastAPI response object used to set the cookie.

    Returns:
        Dict[str, str]: Confirmation message.
    """
    session_id = str(uuid.uuid4())
    token = create_access_token({"sub": session_id})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.SECURE_COOKIE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "Session created.", "session_id": session_id}


@router.post("/logout")
async def logout(response: Response) -> Dict[str, str]:
    """Invalidate the current session by clearing the HttpOnly cookie.

    Args:
        response (Response): FastAPI response object used to delete the cookie.

    Returns:
        Dict[str, str]: Confirmation message.
    """
    response.delete_cookie(
        key="access_token", httponly=True, samesite="lax", secure=settings.SECURE_COOKIE
    )
    return {"message": "Logged out successfully."}
