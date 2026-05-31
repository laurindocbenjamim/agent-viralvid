# -*- coding: utf-8 -*-
"""Unit tests for the clipper video editor: download and crop logic."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.clipper.video_editor import (
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


@patch("backend.app.clipper.video_editor.YoutubeDL")
def test_download_video_calls_ydl(mock_ydl):
    """download_video calls yt-dlp with the correct options."""
    instance = mock_ydl.return_value.__enter__.return_value
    instance.extract_info.return_value = {"id": "abc", "ext": "mp4"}
    result = download_video("https://www.youtube.com/watch?v=abc", "/tmp")
    assert result is not None
    instance.extract_info.assert_called_once()


@patch("backend.app.clipper.video_editor._PILImage")
@patch("backend.app.clipper.video_editor.VideoFileClip")
@patch("backend.app.clipper.video_editor.CompositeVideoClip")
def test_crop_returns_cropped_video(mock_composite, mock_video, mock_pil):
    """crop_and_add_subtitles returns output paths after cropping."""
    import numpy as np

    mock_clip = MagicMock()
    mock_clip.__enter__ = MagicMock(return_value=mock_clip)
    mock_clip.size = (1920, 1080)
    mock_clip.subclip.return_value = mock_clip
    mock_clip.crop.return_value = mock_clip
    mock_clip.duration = 10.0
    mock_clip.get_frame.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_video.return_value = mock_clip
    mock_composite.return_value = mock_clip

    mock_img = MagicMock()
    mock_pil.fromarray.return_value = mock_img
    mock_img.convert.return_value = mock_img

    out_video, out_cover = crop_and_add_subtitles(
        video_path="in.mp4",
        start_sec=0,
        end_sec=30,
        output_path="out.mp4",
    )
    assert out_video == "out.mp4"
    assert out_cover == "out.jpg"
