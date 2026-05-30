# -*- coding: utf-8 -*-
"""Unit tests for the clipper video editor: download and crop/subtitle logic."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.clipper.video_editor import (
    SUBTITLE_POSITIONS,
    SUBTITLE_STYLES,
    crop_and_add_subtitles,
    download_video,
    sanitize_youtube_url,
)


def test_sanitize_valid_youtube_url():
    """Valid YouTube URLs pass sanitisation."""
    url = "https://www.youtube.com/watch?v=abc123"
    assert sanitize_youtube_url(url) == url


def test_sanitize_rejects_non_youtube_url():
    """Non-YouTube URLs raise ValueError."""
    with pytest.raises(ValueError):
        sanitize_youtube_url("https://vimeo.com/12345")


def test_subtitle_style_map_contains_all_keys():
    """All three subtitle styles are registered in the style map."""
    assert "TikTok Bold" in SUBTITLE_STYLES
    assert "Minimalista" in SUBTITLE_STYLES
    assert "Cyberpunk" in SUBTITLE_STYLES


def test_subtitle_position_map_contains_all_keys():
    """All three position keys are registered."""
    assert SUBTITLE_POSITIONS["bottom"] == pytest.approx(0.75)
    assert SUBTITLE_POSITIONS["center"] == pytest.approx(0.50)
    assert SUBTITLE_POSITIONS["top"] == pytest.approx(0.20)


@patch("backend.app.clipper.video_editor.YoutubeDL")
def test_download_video_calls_ydl(mock_ydl):
    """download_video calls yt-dlp with the correct options."""
    instance = mock_ydl.return_value.__enter__.return_value
    instance.extract_info.return_value = {"id": "abc", "ext": "mp4"}
    result = download_video("https://www.youtube.com/watch?v=abc", "/tmp")
    assert result is not None
    instance.extract_info.assert_called_once()


@patch("backend.app.clipper.video_editor.VideoFileClip")
@patch("backend.app.clipper.video_editor.TextClip")
@patch("backend.app.clipper.video_editor.CompositeVideoClip")
def test_crop_and_add_subtitles_cyberpunk(mock_composite, mock_text, mock_video):
    """crop_and_add_subtitles applies Cyberpunk neon-green style correctly."""
    mock_clip = MagicMock()
    mock_clip.__enter__ = MagicMock(return_value=mock_clip)
    mock_clip.size = (1920, 1080)
    mock_clip.subclip.return_value = mock_clip
    mock_clip.crop.return_value = mock_clip
    mock_video.return_value = mock_clip

    mock_txt = MagicMock()
    mock_txt.set_position.return_value = mock_txt
    mock_txt.set_duration.return_value = mock_txt
    mock_text.return_value = mock_txt
    mock_composite.return_value = MagicMock()

    out_video, out_cover = crop_and_add_subtitles(
        video_path="in.mp4",
        start_sec=0,
        end_sec=30,
        output_path="out.mp4",
        subtitle_style="Cyberpunk",
        subtitle_position="top",
    )
    assert out_video == "out.mp4"
    assert out_cover == "out.jpg"
    _, kwargs = mock_text.call_args
    assert kwargs["color"] == "#39FF14"
