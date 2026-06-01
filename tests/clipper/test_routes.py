# -*- coding: utf-8 -*-
"""Integration tests for clipper routes: submission, polling, and options."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.app.auth.security import create_access_token
from backend.app.main import app

client = TestClient(app)


def _authenticated_client():
    """Return a TestClient with a valid session cookie pre-set."""
    token = create_access_token({"sub": "test-session-xyz"})
    client.cookies.set("access_token", token)
    return client


def test_get_options_returns_all_fields():
    """GET /api/clipper/options returns all configurable option lists."""
    response = client.get("/api/clipper/options")
    assert response.status_code == 200
    data = response.json()
    assert "clip_objectives" in data
    assert "subtitle_styles" in data
    assert "TikTok Bold" in data["subtitle_styles"]
    assert "Cyberpunk" in data["subtitle_styles"]


def test_submit_without_cookie_returns_401():
    """Submitting without a session cookie returns 401."""
    bare = TestClient(app)
    response = bare.post(
        "/api/clipper/submit",
        json={"video_source": "https://www.youtube.com/watch?v=test", "video_language": "pt-BR"},
    )
    assert response.status_code == 401


@patch("backend.app.clipper.routes.process_video_pipeline")
@patch("backend.app.clipper.routes.set_task_status")
@patch("backend.app.clipper.routes.save_sqlite_task")
def test_submit_valid_payload_returns_202(mock_sqlite, mock_redis, mock_pipeline):
    """Valid authenticated submission returns 202 with a task_id."""
    mock_redis.return_value = None
    mock_sqlite.return_value = None
    mock_pipeline.return_value = None

    c = _authenticated_client()
    response = c.post(
        "/api/clipper/submit",
        json={
            "video_source": "https://www.youtube.com/watch?v=kwEtOyaFhCA",
            "video_language": "pt-BR",
            "clip_objective": "Viral/Engraçado",
            "target_duration": "30-60",
            "max_clips": 3,
            "subtitle_style": "TikTok Bold",
            "subtitle_position": "bottom",
            "crop_mode": "center",
        },
    )
    assert response.status_code == 202
    assert "task_id" in response.json()


def test_submit_invalid_objective_returns_422():
    """Submitting an unrecognised clip_objective returns 422 Unprocessable Entity."""
    c = _authenticated_client()
    response = c.post(
        "/api/clipper/submit",
        json={
            "video_source": "https://www.youtube.com/watch?v=test",
            "video_language": "pt-BR",
            "clip_objective": "INVALID_OBJECTIVE",
        },
    )
    assert response.status_code == 422


def test_submit_invalid_subtitle_style_returns_422():
    """Submitting an unknown subtitle_style returns 422."""
    c = _authenticated_client()
    response = c.post(
        "/api/clipper/submit",
        json={
            "video_source": "https://www.youtube.com/watch?v=test",
            "video_language": "en-US",
            "subtitle_style": "UNKNOWN_STYLE",
        },
    )
    assert response.status_code == 422


@patch("backend.app.clipper.routes.get_task_status")
def test_get_status_existing_task(mock_status):
    """Polling an existing task returns its status."""
    mock_status.return_value = "Analisando"
    response = client.get("/api/clipper/status/some-task-id")
    assert response.status_code == 200
    assert response.json()["status"] == "Analisando"


@patch("backend.app.clipper.routes.get_task_status")
def test_get_status_unknown_task_returns_404(mock_status):
    """Polling an unknown task ID returns 404."""
    mock_status.return_value = None
    response = client.get("/api/clipper/status/nonexistent-id")
    assert response.status_code == 404


def test_submit_invalid_subtitle_font_size_returns_422():
    """Submitting an invalid subtitle_font_size (e.g. out of range) returns 422."""
    c = _authenticated_client()
    response = c.post(
        "/api/clipper/submit",
        json={
            "video_source": "https://www.youtube.com/watch?v=test",
            "video_language": "en-US",
            "subtitle_font_size": 200,  # Max is 150
        },
    )
    assert response.status_code == 422


def test_submit_valid_subtitle_font_size_returns_202():
    """Submitting a valid subtitle_font_size returns 202."""
    c = _authenticated_client()
    with patch("backend.app.clipper.routes.process_video_pipeline") as mock_pipeline, \
         patch("backend.app.clipper.routes.set_task_status") as mock_redis, \
         patch("backend.app.clipper.routes.save_sqlite_task") as mock_sqlite:
        mock_redis.return_value = None
        mock_sqlite.return_value = None
        mock_pipeline.return_value = None

        response = c.post(
            "/api/clipper/submit",
            json={
                "video_source": "https://www.youtube.com/watch?v=test",
                "video_language": "en-US",
                "subtitle_font_size": 50,
            },
        )
        assert response.status_code == 202

