# -*- coding: utf-8 -*-
"""Unit tests to verify the corrected subtitle positions and styles."""

from backend.app.clipper.video_editor import SUBTITLE_POSITIONS, SUBTITLE_STYLES


def test_subtitle_positions_in_safe_zone():
    """Verify that 'top' and 'bottom' are within the 70% to 80% Safe Zone."""
    assert "top" in SUBTITLE_POSITIONS
    assert "bottom" in SUBTITLE_POSITIONS
    assert "center" in SUBTITLE_POSITIONS

    # Safe zone constraint: 0.70 <= ratio <= 0.80
    assert 0.70 <= SUBTITLE_POSITIONS["top"] <= 0.80
    assert 0.70 <= SUBTITLE_POSITIONS["bottom"] <= 0.80

    # Ensure top is slightly higher (smaller ratio value) than bottom
    assert SUBTITLE_POSITIONS["top"] < SUBTITLE_POSITIONS["bottom"]

    # Center should remain in the middle range
    assert 0.40 <= SUBTITLE_POSITIONS["center"] <= 0.50


def test_subtitle_font_sizes_increased():
    """Verify that subtitle font sizes have been increased for visibility."""
    assert SUBTITLE_STYLES["TikTok Bold"]["font_size"] == 76
    assert SUBTITLE_STYLES["Minimalista"]["font_size"] == 56
    assert SUBTITLE_STYLES["Cyberpunk"]["font_size"] == 68


def test_subtitle_font_size_override():
    """Verify that crop_and_add_subtitles signature supports custom subtitle_font_size."""
    import inspect
    from backend.app.clipper.video_editor import crop_and_add_subtitles
    sig = inspect.signature(crop_and_add_subtitles)
    assert "subtitle_font_size" in sig.parameters
    assert sig.parameters["subtitle_font_size"].default is None

