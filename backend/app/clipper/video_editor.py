# -*- coding: utf-8 -*-
"""Clipper bounded context: yt-dlp downloader and MoviePy vertical renderer."""

import logging
import os
import re
from typing import Literal, Tuple

from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip, ColorClip
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Subtitle style configuration map (Rule 3 – zero hard-coded magic values)
# ---------------------------------------------------------------------------
SUBTITLE_STYLES = {
    "TikTok Bold": {"color": "yellow", "font": "Arial-Bold", "stroke_width": 3},
    "Minimalista": {"color": "white", "font": "Arial", "stroke_width": 1},
    "Cyberpunk": {"color": "#39FF14", "font": "Impact", "stroke_width": 3},
}

SUBTITLE_POSITIONS = {"bottom": 0.75, "center": 0.50, "top": 0.20}

YT_PATTERN = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")


def sanitize_youtube_url(url: str) -> str:
    """Validate and sanitise a YouTube URL to prevent command injection.

    Args:
        url (str): Raw URL string from user input.

    Returns:
        str: Validated URL safe for downstream use.

    Raises:
        ValueError: If the URL does not match the expected YouTube pattern.
    """
    if not YT_PATTERN.match(url):
        raise ValueError("Invalid YouTube URL pattern.")
    return url


def download_video(url: str, output_dir: str) -> str:
    """Download a YouTube video using yt-dlp.

    Args:
        url (str): Validated YouTube URL.
        output_dir (str): Directory to store the downloaded file.

    Returns:
        str: Absolute path of the downloaded video file.
    """
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


def crop_and_add_subtitles(
    video_path: str,
    start_sec: int,
    end_sec: int,
    output_path: str,
    subtitle_text: str = "VIRAL MOMENT",
    subtitle_style: str = "TikTok Bold",
    subtitle_position: Literal["bottom", "center", "top"] = "bottom",
    crop_mode: Literal["center", "fit", "smart_track"] = "fit",
) -> str:
    """Crop a horizontal clip to 9:16 and overlay styled subtitles.

    Args:
        video_path (str): Path to the source horizontal video.
        start_sec (int): Clip start timestamp in seconds.
        end_sec (int): Clip end timestamp in seconds.
        output_path (str): Destination path for the rendered vertical clip.
        subtitle_text (str): Text to overlay on the video.
        subtitle_style (str): One of "TikTok Bold", "Minimalista", "Cyberpunk".
        subtitle_position (str): Vertical alignment ("bottom", "center", "top").
        crop_mode (str): Mode for making it vertical ("fit" letterboxes, "center" crops).

    Returns:
        Tuple[str, str]: Paths to the rendered output video file and the extracted thumbnail image.
    """
    style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["TikTok Bold"])
    position_ratio = SUBTITLE_POSITIONS.get(subtitle_position, 0.75)

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with VideoFileClip(video_path) as clip:
        subclip = clip.subclip(start_sec, end_sec)
        original_w, original_h = subclip.size
        
        if crop_mode == "fit":
            target_w = original_w
            target_h = int(original_w * (16 / 9))
            bg = ColorClip(size=(target_w, target_h), color=(0,0,0)).set_duration(subclip.duration)
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

        try:
            txt_clip = TextClip(
                txt=subtitle_text.upper(),
                fontsize=70,
                color=style["color"],
                font=style["font"],
                stroke_color="black",
                stroke_width=style["stroke_width"],
                method="label",
                size=(target_w - 40, None),
            )
            txt_clip = txt_clip.set_position(
                ("center", int(target_h * position_ratio))
            ).set_duration(cropped.duration)
            final = CompositeVideoClip([cropped, txt_clip])
        except Exception as exc:
            logger.warning("Subtitle render failed (%s). Using crop-only.", exc)
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
            threads=os.cpu_count() or 4
        )

        cover_path = output_path.rsplit(".", 1)[0] + ".jpg"
        duration = final.duration
        if isinstance(duration, (int, float)):
            t_sec = min(1.0, duration / 2)
        else:
            t_sec = 1.0
        final.save_frame(cover_path, t=t_sec)

    return output_path, cover_path
