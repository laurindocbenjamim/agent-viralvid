# -*- coding: utf-8 -*-
"""Clipper bounded context: REST endpoints for job submission and status polling."""

import html
import json
import uuid
import os
import shutil
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field, field_validator

from backend.app.auth.security import get_session_from_cookie
from backend.app.clipper.tasks import process_video_pipeline
from backend.app.core.database import (
    get_cached_results,
    get_task_status,
    save_sqlite_task,
    set_task_status,
)

router = APIRouter(prefix="/api/clipper", tags=["clipper"])

_VALID_OBJECTIVES = {
    "Viral/Engraçado",
    "Educacional/Informativo",
    "Polémico",
    "Motivacional",
    "Melhores Momentos (Highlights)",
}
_VALID_DURATIONS = {"15-30", "30-60", "60-90"}
_VALID_STYLES = {"TikTok Bold", "Minimalista", "Cyberpunk"}
_VALID_POSITIONS = {"bottom", "center", "top"}
_VALID_CROPS = {"center", "fit", "smart_track"}


class ClipperSubmitPayload(BaseModel):
    """Validated and sanitised payload for a new clipper job submission."""

    video_source: str = Field(..., description="YouTube URL or local file path.")
    video_language: str = Field(..., min_length=2, max_length=10)
    clip_objective: str = Field("Viral/Engraçado")
    target_duration: str = Field("30-60")
    max_clips: int = Field(3, ge=1, le=5)
    subtitle_style: str = Field("TikTok Bold")
    subtitle_position: str = Field("bottom")
    crop_mode: str = Field("fit")
    subtitle_font_size: Optional[int] = Field(None, ge=10, le=150, description="Custom subtitle font size.")

    @field_validator("clip_objective")
    @classmethod
    def validate_objective(cls, v: str) -> str:
        """Ensure clip_objective is a recognised content goal."""
        if v not in _VALID_OBJECTIVES:
            raise ValueError(f"clip_objective must be one of {_VALID_OBJECTIVES}")
        return v

    @field_validator("target_duration")
    @classmethod
    def validate_duration(cls, v: str) -> str:
        """Ensure target_duration is a recognised duration key."""
        if v not in _VALID_DURATIONS:
            raise ValueError(f"target_duration must be one of {_VALID_DURATIONS}")
        return v

    @field_validator("subtitle_style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        """Ensure subtitle_style is a recognised visual theme."""
        if v not in _VALID_STYLES:
            raise ValueError(f"subtitle_style must be one of {_VALID_STYLES}")
        return v

    @field_validator("subtitle_position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        """Ensure subtitle_position is a recognised placement option."""
        if v not in _VALID_POSITIONS:
            raise ValueError(f"subtitle_position must be one of {_VALID_POSITIONS}")
        return v

    @field_validator("crop_mode")
    @classmethod
    def validate_crop(cls, v: str) -> str:
        """Ensure crop_mode is a recognised frame mode."""
        if v not in _VALID_CROPS:
            raise ValueError(f"crop_mode must be one of {_VALID_CROPS}")
        return v

    @field_validator("video_language")
    @classmethod
    def sanitize_language(cls, v: str) -> str:
        """Strip and escape the language code to prevent injection."""
        return html.escape(v.strip())


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    payload: ClipperSubmitPayload,
    background_tasks: BackgroundTasks,
    session: str = Depends(get_session_from_cookie),
) -> Dict[str, str]:
    """Submit a new video clipping job to the background pipeline.

    Args:
        payload (ClipperSubmitPayload): Validated job configuration.
        background_tasks (BackgroundTasks): FastAPI background task registry.
        session (str): Session identifier from the validated cookie.

    Returns:
        Dict[str, str]: Task ID and initial status.
    """
    task_id = str(uuid.uuid4())
    await set_task_status(task_id, "Baixando")
    await save_sqlite_task(task_id, session, payload.video_source, "Baixando")
    background_tasks.add_task(
        process_video_pipeline,
        video_url=payload.video_source,
        user_id=session,
        task_id=task_id,
        video_language=payload.video_language,
        clip_objective=payload.clip_objective,
        target_duration=payload.target_duration,
        max_clips=payload.max_clips,
        subtitle_style=payload.subtitle_style,
        subtitle_position=payload.subtitle_position,
        crop_mode=payload.crop_mode,
        subtitle_font_size=payload.subtitle_font_size,
    )
    return {"task_id": task_id, "status": "Baixando"}


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_job(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    video_language: str = Form("en-US"),
    clip_objective: str = Form("Viral/Engraçado"),
    target_duration: str = Form("30-60"),
    max_clips: int = Form(3),
    subtitle_style: str = Form("TikTok Bold"),
    subtitle_position: str = Form("bottom"),
    crop_mode: str = Form("fit"),
    subtitle_font_size: Optional[int] = Form(None),
    session: str = Depends(get_session_from_cookie),
) -> Dict[str, str]:
    """Submit a local video file for clipping."""
    task_id = str(uuid.uuid4())
    temp_dir = f"./backend/temp/{task_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    file_path = os.path.join(temp_dir, video_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(video_file.file, buffer)
        
    await set_task_status(task_id, "Processando")
    await save_sqlite_task(task_id, session, f"upload:{video_file.filename}", "Processando")
    
    background_tasks.add_task(
        process_video_pipeline,
        video_url=file_path,
        user_id=session,
        task_id=task_id,
        video_language=video_language,
        clip_objective=clip_objective,
        target_duration=target_duration,
        max_clips=max_clips,
        subtitle_style=subtitle_style,
        subtitle_position=subtitle_position,
        crop_mode=crop_mode,
        subtitle_font_size=subtitle_font_size,
    )
    return {"task_id": task_id, "status": "Processando"}


@router.get("/status/{task_id}")
async def get_status(task_id: str) -> Dict[str, Any]:
    """Poll the current status and results of a submitted clipping job.

    Args:
        task_id (str): The unique task identifier returned at submission.

    Returns:
        Dict[str, Any]: Current status and rendered clip list if completed.

    Raises:
        HTTPException: 404 if the task ID is not found in Redis.
    """
    safe_id = html.escape(task_id)
    current = await get_task_status(safe_id)
    if not current:
        raise HTTPException(status_code=404, detail="Task not found.")

    payload: Dict[str, Any] = {"task_id": safe_id, "status": current, "clips": []}
    if current == "Concluido":
        raw = await get_cached_results(safe_id)
        if raw:
            payload["clips"] = json.loads(raw)
    return payload


@router.get("/options")
async def get_options() -> Dict[str, List[str]]:
    """Return all valid option sets for frontend dropdowns.

    Returns:
        Dict[str, List[str]]: Available choices for each configurable field.
    """
    return {
        "clip_objectives": sorted(_VALID_OBJECTIVES),
        "target_durations": sorted(_VALID_DURATIONS),
        "subtitle_styles": sorted(_VALID_STYLES),
        "subtitle_positions": sorted(_VALID_POSITIONS),
        "crop_modes": sorted(_VALID_CROPS),
    }
