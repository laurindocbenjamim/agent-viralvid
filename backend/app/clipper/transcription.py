# -*- coding: utf-8 -*-
"""Clipper bounded context: audio extraction and speech-to-text transcription."""

import logging
import os
import tempfile
from typing import Any, Dict, List

import httpx
from moviepy.editor import VideoFileClip

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def extract_audio(video_path: str, start_sec: float, end_sec: float) -> str:
    """Extract audio from a video segment and save as WAV.

    Args:
        video_path: Path to the source video file.
        start_sec: Start timestamp in seconds.
        end_sec: End timestamp in seconds.

    Returns:
        Path to the temporary WAV file.
    """
    with VideoFileClip(video_path) as clip:
        subclip = clip.subclip(start_sec, end_sec)
        audio_path = tempfile.mktemp(suffix=".wav")
        subclip.audio.write_audiofile(
            audio_path,
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            verbose=False,
            logger=None,
        )
        return audio_path


def transcribe_audio(audio_path: str) -> List[Dict[str, Any]]:
    """Transcribe audio using Groq Whisper STT with word-level timestamps.

    Args:
        audio_path: Path to the WAV audio file.

    Returns:
        List of word segments: [{"word": str, "start": float, "end": float}, ...]
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured.")

    with open(audio_path, "rb") as f:
        response = httpx.post(
            GROQ_STT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            data={
                "model": settings.GROQ_STT_MODEL,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "word",
            },
            files={"file": ("audio.wav", f, "audio/wav")},
            timeout=60.0,
        )

    if response.status_code != 200:
        raise RuntimeError(f"Groq STT failed ({response.status_code}): {response.text}")

    data = response.json()
    words = data.get("words", [])
    logger.info("Transcribed %d words from %s", len(words), audio_path)
    return words


def build_subtitle_phrases(
    words: List[Dict[str, Any]],
    max_words_per_phrase: int = 5,
    max_duration_per_phrase: float = 4.0,
) -> List[Dict[str, Any]]:
    """Group individual word segments into subtitle phrases.

    Args:
        words: List of {"word": str, "start": float, "end": float}.
        max_words_per_phrase: Maximum words per subtitle line.
        max_duration_per_phrase: Maximum duration in seconds per phrase.

    Returns:
        List of {"text": str, "start_offset": float, "end_offset": float}.
    """
    if not words:
        return []

    phrases: List[Dict[str, Any]] = []
    current_words: List[str] = []
    current_start: float = words[0]["start"]
    current_end: float = words[0]["end"]

    for w in words:
        word_text = w["word"]
        word_start = w["start"]
        word_end = w["end"]

        # Check if we should start a new phrase
        phrase_duration = word_end - current_start
        if (
            len(current_words) >= max_words_per_phrase
            or phrase_duration > max_duration_per_phrase
        ):
            # Emit current phrase
            phrases.append({
                "text": " ".join(current_words),
                "start_offset": round(current_start, 3),
                "end_offset": round(current_end, 3),
            })
            current_words = []
            current_start = word_start

        current_words.append(word_text)
        current_end = word_end

    # Emit final phrase
    if current_words:
        phrases.append({
            "text": " ".join(current_words),
            "start_offset": round(current_start, 3),
            "end_offset": round(current_end, 3),
        })

    return phrases


def transcribe_clip(
    video_path: str,
    start_sec: float,
    end_sec: float,
) -> List[Dict[str, Any]]:
    """Full pipeline: extract audio → transcribe → build subtitle phrases.

    Args:
        video_path: Path to the source video file.
        start_sec: Clip start timestamp in seconds.
        end_sec: Clip end timestamp in seconds.

    Returns:
        List of timed subtitle phrases ready for rendering.
    """
    audio_path = None
    try:
        audio_path = extract_audio(video_path, start_sec, end_sec)
        words = transcribe_audio(audio_path)
        phrases = build_subtitle_phrases(words)
        return phrases
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
