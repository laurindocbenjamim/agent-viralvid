# -*- coding: utf-8 -*-
"""Clipper bounded context: yt-dlp downloader and MoviePy vertical renderer."""

import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from moviepy.editor import CompositeVideoClip, VideoFileClip, ColorClip
from PIL import Image as _PILImage, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

YT_PATTERN = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")

SUBTITLE_STYLES: Dict[str, Dict[str, Any]] = {
    "TikTok Bold": {
        "color": (255, 255, 0),
        "highlight_color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "font_size": 52,
        "stroke_width": 3,
    },
    "Minimalista": {
        "color": (255, 255, 255),
        "highlight_color": (255, 255, 0),
        "stroke_color": (0, 0, 0),
        "font_size": 44,
        "stroke_width": 1,
    },
    "Cyberpunk": {
        "color": (57, 255, 20),
        "highlight_color": (255, 0, 255),
        "stroke_color": (0, 0, 0),
        "font_size": 52,
        "stroke_width": 3,
    },
}

SUBTITLE_POSITIONS: Dict[str, float] = {"bottom": 0.72, "center": 0.45, "top": 0.18}

PADDING_X = 32
PADDING_Y = 16


def sanitize_youtube_url(url: str) -> str:
    if not YT_PATTERN.match(url):
        raise ValueError("Invalid YouTube URL pattern.")
    return url


def download_video(url: str, output_dir: str) -> str:
    sanitized = sanitize_youtube_url(url)
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/18/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(sanitized, download=True)
        filename = ydl.prepare_filename(info)
        logger.info("Downloaded video to %s", filename)
        return filename


# ---------------------------------------------------------------------------
# Pillow-based subtitle renderer (no ImageMagick dependency)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a bold TrueType font, falling back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Word-wrap text so each line fits within max_width pixels."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


def _render_subtitle_frame(
    frame: np.ndarray,
    phrases: List[Dict[str, Any]],
    t: float,
    target_w: int,
    target_h: int,
    style: Dict[str, Any],
    position_ratio: float,
) -> np.ndarray:
    """Render subtitle phrases onto a frame at time t using Pillow.

    Only the phrase whose time window contains t is rendered.  UPPERCASE
    tokens are drawn in ``highlight_color`` for emphasis.  Text is always
    centred horizontally and stays within the visible area.
    """
    active = None
    for p in phrases:
        s = float(p.get("start_offset", 0))
        e = float(p.get("end_offset", s + 1))
        if s <= t < e:
            active = p
            break
    if active is None:
        return frame

    raw_text = (active.get("text") or "").strip()
    if not raw_text:
        return frame

    font_size = style["font_size"]
    font = _load_font(font_size)
    base_color = style["color"]
    hl_color = style["highlight_color"]
    stroke_w = style["stroke_width"]

    draw_area_w = target_w - 2 * PADDING_X
    lines = _wrap_text(raw_text.upper(), font, draw_area_w)

    # Measure total text block height
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = font.getbbox(line)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    line_gap = 8
    total_h = sum(line_heights) + line_gap * (len(lines) - 1) if lines else 0

    # Y position: centred around the target ratio
    y_start = int(target_h * position_ratio - total_h / 2)
    y_start = max(PADDING_Y, min(y_start, target_h - total_h - PADDING_Y))

    # Create RGBA overlay
    overlay = _PILImage.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    y_cursor = y_start
    for line in lines:
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (target_w - lw) // 2  # centred horizontally

        # Draw stroke (outline)
        if stroke_w > 0:
            for dx in range(-stroke_w, stroke_w + 1):
                for dy in range(-stroke_w, stroke_w + 1):
                    if dx * dx + dy * dy <= stroke_w * stroke_w:
                        draw.text((x + dx, y_cursor + dy), line, font=font, fill=(0, 0, 0, 255))

        # Draw text — highlight uppercase words differently
        words = line.split()
        x_cursor = x
        for word in words:
            is_hl = word.isupper() and len(word) > 1
            color = hl_color if is_hl else base_color
            # Stroke for each word
            if stroke_w > 0:
                for dx in range(-stroke_w, stroke_w + 1):
                    for dy in range(-stroke_w, stroke_w + 1):
                        if dx * dx + dy * dy <= stroke_w * stroke_w:
                            draw.text((x_cursor + dx, y_cursor + dy), word + " ",
                                      font=font, fill=(0, 0, 0, 255))
            draw.text((x_cursor, y_cursor), word + " ", font=font, fill=(*color, 255))
            w_bbox = font.getbbox(word + " ")
            x_cursor += w_bbox[2] - w_bbox[0]

        y_cursor += (bbox[3] - bbox[1]) + line_gap

    # Composite onto frame
    frame_rgba = _PILImage.fromarray(frame).convert("RGBA")
    composited = _PILImage.alpha_composite(frame_rgba, overlay)
    return np.array(composited.convert("RGB"))


def crop_and_add_subtitles(
    video_path: str,
    start_sec: int,
    end_sec: int,
    output_path: str,
    subtitle_text: str = "",
    subtitle_style: str = "TikTok Bold",
    subtitle_position: Literal["bottom", "center", "top"] = "bottom",
    crop_mode: Literal["center", "fit", "smart_track"] = "fit",
    subtitles: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """Crop a horizontal clip to 9:16 and overlay centred subtitles.

    Each subtitle phrase is rendered via Pillow (no ImageMagick needed),
    centred horizontally and positioned vertically at *subtitle_position*.
    Only one phrase is visible at a time so they never overlap.
    """
    style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["TikTok Bold"])
    position_ratio = SUBTITLE_POSITIONS.get(subtitle_position, 0.72)

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with VideoFileClip(video_path) as clip:
        subclip = clip.subclip(start_sec, end_sec)
        original_w, original_h = subclip.size

        if crop_mode == "fit":
            target_w = original_w
            target_h = int(original_w * (16 / 9))
            bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0)).set_duration(
                subclip.duration
            )
            cropped = CompositeVideoClip([bg, subclip.set_position("center")])
        else:
            target_w = int(original_h * (9 / 16))
            target_h = original_h
            cropped = subclip.crop(
                x_center=original_w / 2,
                y_center=original_h / 2,
                width=target_w,
                height=original_h,
            )

        has_subs = subtitles and len(subtitles) > 0

        if has_subs:
            def apply_subs(get_frame, t):
                frame = get_frame(t)
                return _render_subtitle_frame(
                    frame, subtitles, t, target_w, target_h, style, position_ratio
                )

            final = cropped.fl(apply_subs, apply_to=[])
        else:
            final = cropped

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            verbose=False,
            logger=None,
            bitrate="8000k",
            preset="veryfast",
            threads=os.cpu_count() or 4,
        )

        cover_path = output_path.rsplit(".", 1)[0] + ".jpg"
        duration = final.duration
        t_sec = min(1.0, duration / 2) if isinstance(duration, (int, float)) else 1.0
        frame = final.get_frame(t_sec)
        _PILImage.fromarray(frame).convert("RGB").save(cover_path)

    return output_path, cover_path
