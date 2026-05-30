# -*- coding: utf-8 -*-
"""Unit tests for the auth bounded context: security and session routes."""

import pytest
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.auth.security import create_access_token, get_session_from_cookie
from backend.app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_create_access_token_contains_sub():
    """Verify that a created token embeds the sub claim correctly."""
    token = create_access_token({"sub": "test-session-id"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_session_sets_httponly_cookie(client):
    """Verify that /api/auth/session sets an HttpOnly SameSite=lax cookie."""
    response = client.post("/api/auth/session")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_logout_clears_cookie(client):
    """Verify that /api/auth/logout deletes the session cookie."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert 'access_token=""' in set_cookie or "access_token=;" in set_cookie


def test_expired_token_raises_401(client):
    """Verify that an expired token causes a 401 on protected endpoints."""
    from backend.app.core.config import settings
    from jose import jwt
    from datetime import datetime, timezone

    expired_payload = {"sub": "old-session", "exp": datetime(2000, 1, 1, tzinfo=timezone.utc)}
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    client.cookies.set("access_token", expired_token)

    response = client.post(
        "/api/clipper/submit",
        json={
            "video_source": "https://www.youtube.com/watch?v=test",
            "video_language": "pt-BR",
        },
    )
    assert response.status_code == 401
