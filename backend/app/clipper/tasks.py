# -*- coding: utf-8 -*-
"""Clipper bounded context: background task orchestration pipeline."""

import json
import logging
import os
from typing import Optional

from backend.app.clipper.pipeline import extract_viral_moments
from backend.app.clipper.transcription import transcribe_clip
from backend.app.clipper.video_editor import crop_and_add_subtitles, download_video
from backend.app.core.database import (
    cache_results,
    save_sqlite_task,
    save_sqlite_task_results,
    set_task_status,
)

logger = logging.getLogger(__name__)


async def process_video_pipeline(
    video_url: str,
    user_id: str,
    task_id: str,
    video_language: str,
    clip_objective: str,
    target_duration: str,
    max_clips: int,
    subtitle_style: str,
    subtitle_position: str,
    crop_mode: str = "fit",
    subtitle_font_size: Optional[int] = None,
) -> None:
    """Orchestrate the full video clipping pipeline as a background task.

    Phases: Download → AI Analysis → Render → Persist results.

    Args:
        video_url (str): Validated YouTube source URL.
        user_id (str): Session identifier from the cookie token.
        task_id (str): Unique job identifier.
        video_language (str): Spoken language code (e.g. "pt-BR").
        clip_objective (str): AI content goal selection.
        target_duration (str): Target clip length key (e.g. "30-60").
        max_clips (int): Maximum number of clips to generate.
        subtitle_style (str): Visual subtitle theme.
        subtitle_position (str): Vertical subtitle placement.
        crop_mode (str): Frame scaling behavior ("center" or "fit").
    """
    temp_dir = f"./backend/temp/{task_id}"
    clips_dir = f"./backend/clips/{task_id}"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    async def _update(status: str) -> None:
        await set_task_status(task_id, status)
        await save_sqlite_task(task_id, user_id, video_url, status)

    try:
        await _update("Baixando")
        if video_url.startswith("http://") or video_url.startswith("https://"):
            video_path = download_video(video_url, temp_dir)
        else:
            # Local uploaded file
            video_path = video_url

        await _update("Analisando")
        mock_transcript = (
            "Hoje vou revelar o maior segredo do algoritmo do TikTok. "
            "O gancho inicial é tudo — se não prender nos primeiros 3 segundos, perdeste. "
            "Legendas grandes, coloridas, com contorno preto. Corte 9:16 centrado."
        )
        moments = await extract_viral_moments(
            transcript=mock_transcript,
            video_language=video_language,
            clip_objective=clip_objective,
            target_duration=target_duration,
            max_clips=max_clips,
        )

        await _update("Renderizando")
        rendered_clips = []
        for moment in moments:
            clip_filename = f"clip_{moment['id']}.mp4"
            output_path = os.path.join(clips_dir, clip_filename)
            start_sec = moment.get("inicio_segundos", 0)
            end_sec = moment.get("fim_segundos", 30)

            # Real speech-to-text with word-level timestamps
            await _update(f"Transcrevendo clipe {moment['id']}...")
            try:
                subtitles = transcribe_clip(video_path, start_sec, end_sec)
            except Exception as exc:
                logger.warning("Transcription failed for clip %d: %s", moment["id"], exc)
                subtitles = []

            output_path, cover_path = crop_and_add_subtitles(
                video_path=video_path,
                start_sec=start_sec,
                end_sec=end_sec,
                output_path=output_path,
                subtitle_text=moment.get("titulo", "Viral"),
                subtitle_style=subtitle_style,
                subtitle_position=subtitle_position,
                crop_mode=crop_mode,
                subtitles=subtitles,
                subtitle_font_size=subtitle_font_size,
            )
            cover_filename = os.path.basename(cover_path)
            rendered_clips.append({
                "clip_id": moment["id"],
                "titulo": moment["titulo"],
                "justificativa": moment.get("justificativa", ""),
                "transcription": subtitles,
                "url_path": f"/clips/{task_id}/{clip_filename}",
                "thumb_url": f"/clips/{task_id}/{cover_filename}",
            })

        clips_json = json.dumps(rendered_clips)
        await cache_results(task_id, clips_json)
        await save_sqlite_task_results(task_id, "Concluido", clips_json)
        await set_task_status(task_id, "Concluido")
        logger.info("Pipeline complete for task %s", task_id)

    except Exception as exc:
        logger.exception("Pipeline failed for task %s", task_id)
        error_status = f"Erro: {str(exc)[:120]}"
        await set_task_status(task_id, error_status)
        await save_sqlite_task_results(task_id, error_status, json.dumps([]))
    finally:
        _cleanup(temp_dir)


def _cleanup(temp_dir: str) -> None:
    """Remove temporary source files after processing to prevent storage leaks.

    Args:
        temp_dir (str): Path to the temporary download directory.
    """
    try:
        if os.path.exists(temp_dir):
            for fname in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, fname))
            os.rmdir(temp_dir)
    except Exception as exc:
        logger.error("Cleanup failed for %s: %s", temp_dir, exc)
