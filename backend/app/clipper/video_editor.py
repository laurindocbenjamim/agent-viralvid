# -*- coding: utf-8 -*-
"""Clipper bounded context: yt-dlp downloader and MoviePy vertical renderer."""

import logging
import os
import re
from typing import Tuple

from moviepy.editor import CompositeVideoClip, VideoFileClip, ColorClip
from PIL import Image as _PILImage
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

YT_PATTERN = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")


def sanitize_youtube_url(url: str) -> str:
    """Validate and sanitise a YouTube URL to prevent command injection."""
    if not YT_PATTERN.match(url):
        raise ValueError("Invalid YouTube URL pattern.")
    return url


def download_video(url: str, output_dir: str) -> str:
    """Download a YouTube video using yt-dlp."""
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
    subtitle_text: str = "",
    subtitle_style: str = "TikTok Bold",
    subtitle_position: str = "bottom",
    crop_mode: str = "fit",
    subtitles=None,
) -> Tuple[str, str]:
    """Crop a horizontal clip to 9:16 and extract a thumbnail.

    Args:
        video_path: Path to the source horizontal video.
        start_sec: Clip start timestamp in seconds.
        end_sec: Clip end timestamp in seconds.
        output_path: Destination path for the rendered vertical clip.
        subtitle_text: Ignored (kept for API compatibility).
        subtitle_style: Ignored.
        subtitle_position: Ignored.
        crop_mode: Mode for making it vertical ("fit" letterboxes, "center" crops).
        subtitles: Ignored.

    Returns:
        Tuple of (output_video_path, thumbnail_jpg_path).
    """
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

        cropped.write_videofile(
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
        duration = cropped.duration
        if isinstance(duration, (int, float)):
            t_sec = min(1.0, duration / 2)
        else:
            t_sec = 1.0
        frame = cropped.get_frame(t_sec)
        _PILImage.fromarray(frame).convert("RGB").save(cover_path)

    return output_path, cover_path
