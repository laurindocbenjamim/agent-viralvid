# -*- coding: utf-8 -*-
"""Unit tests for the clipper background task pipeline orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.clipper.tasks import process_video_pipeline


@pytest.mark.asyncio
@patch("backend.app.clipper.tasks.download_video")
@patch("backend.app.clipper.tasks.extract_viral_moments")
@patch("backend.app.clipper.tasks.crop_and_add_subtitles")
@patch("backend.app.clipper.tasks.set_task_status")
@patch("backend.app.clipper.tasks.save_sqlite_task")
@patch("backend.app.clipper.tasks.save_sqlite_task_results")
@patch("backend.app.clipper.tasks.cache_results")
async def test_pipeline_runs_all_phases(
    mock_cache, mock_results, mock_sqlite, mock_status,
    mock_crop, mock_extract, mock_download,
):
    """Verify the pipeline transitions through all four status phases."""
    mock_download.return_value = "/tmp/video.mp4"
    mock_extract.return_value = [
        {"id": 1, "inicio_segundos": 10, "fim_segundos": 40,
         "titulo": "Corte Viral", "justificativa": "Forte gancho."}
    ]
    mock_crop.return_value = ("/tmp/clip_1.mp4", "/tmp/clip_1.jpg")
    mock_status.return_value = None
    mock_sqlite.return_value = None
    mock_results.return_value = None

    await process_video_pipeline(
        video_url="https://www.youtube.com/watch?v=kwEtOyaFhCA",
        user_id="session-test",
        task_id="task-e2e-001",
        video_language="pt-BR",
        clip_objective="Viral/Engraçado",
        target_duration="30-60",
        max_clips=1,
        subtitle_style="TikTok Bold",
        subtitle_position="bottom",
    )

    mock_status.assert_any_call("task-e2e-001", "Baixando")
    mock_status.assert_any_call("task-e2e-001", "Analisando")
    mock_status.assert_any_call("task-e2e-001", "Renderizando")
    mock_status.assert_any_call("task-e2e-001", "Concluido")
    mock_download.assert_called_once()
    mock_extract.assert_called_once()
    mock_crop.assert_called_once()
