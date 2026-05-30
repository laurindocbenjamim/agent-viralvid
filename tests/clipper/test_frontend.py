# -*- coding: utf-8 -*-
"""Integration tests verifying the root route and premium video player components in served frontend."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_serve_frontend_returns_200():
    """Verify that root route serves index.html successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_frontend_has_premium_play_controls():
    """Verify index.html contains necessary CSS classes and looping video tags."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.text

    assert "ViralVid AI Clipper" in html_content
    assert 'class="clip-video"' in html_content
    assert "loop" in html_content


def test_frontend_has_custom_play_toggle_script():
    """Verify index.html contains the custom togglePlay handler and play overlay styling."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.text

    assert "function togglePlay" in html_content
    assert ".play-overlay.playing" in html_content


def test_frontend_has_download_button():
    """Verify index.html contains the download button class and helper function."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.text

    assert "btn-download" in html_content
    assert "function downloadClip" in html_content


def test_frontend_has_file_upload_zone():
    """Verify index.html contains the file upload drop zone and source tabs."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.text

    assert 'id="dropZone"' in html_content
    assert 'id="fileInput"' in html_content
    assert "function switchSource" in html_content
    assert "Upload File" in html_content


def test_frontend_video_not_zoomed():
    """Verify video uses object-fit: contain and max-height, not aspect-ratio: 9/16."""
    response = client.get("/")
    assert response.status_code == 200
    html_content = response.text

    assert "object-fit: contain" in html_content
    assert "max-height: 320px" in html_content
    # The forced 9:16 aspect-ratio that caused zoom must NOT be present
    assert "aspect-ratio: 9/16" not in html_content
