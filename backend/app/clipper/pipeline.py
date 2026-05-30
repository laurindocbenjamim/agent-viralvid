# -*- coding: utf-8 -*-
"""Clipper bounded context: AI viral moment extraction via LangChain + Groq."""

import logging
from typing import List

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class ViralMoment(BaseModel):
    """Schema for a single AI-identified viral video segment."""

    id: int = Field(..., description="Ordered index of the clip.")
    inicio_segundos: int = Field(..., ge=0, description="Start timestamp in seconds.")
    fim_segundos: int = Field(..., ge=1, description="End timestamp in seconds.")
    titulo: str = Field(..., description="High-impact TikTok hook title.")
    justificativa: str = Field(..., description="Why this moment is viral.")


class ViralMomentsResponse(BaseModel):
    """Container for all extracted viral moments."""

    momentos: List[ViralMoment]


_OBJECTIVE_MAP = {
    "Viral/Engraçado": "funny, highly shareable, humour-driven moments",
    "Educacional/Informativo": "clear, insightful, educational takeaways",
    "Polémico": "controversial, debate-triggering, opinionated statements",
    "Motivacional": "inspiring, emotionally charged, motivational highlights",
    "Melhores Momentos (Highlights)": "the overall best and most memorable highlights",
}

_DURATION_MAP = {
    "15-30": "between 15 and 30",
    "30-60": "between 30 and 60",
    "60-90": "between 60 and 90",
}


async def extract_viral_moments(
    transcript: str,
    video_language: str,
    clip_objective: str,
    target_duration: str,
    max_clips: int,
) -> List[dict]:
    """Extract viral clip moments from a video transcript using the Groq LLM.

    Args:
        transcript (str): Full video transcript text.
        video_language (str): Language code of the spoken content (e.g. "pt-BR").
        clip_objective (str): Content goal key (e.g. "Viral/Engraçado").
        target_duration (str): Target clip length key (e.g. "30-60").
        max_clips (int): Maximum number of clips to extract (1–5).

    Returns:
        List[dict]: Serialised ViralMoment dictionaries.
    """
    objective_desc = _OBJECTIVE_MAP.get(clip_objective, "highly engaging moments")
    duration_desc = _DURATION_MAP.get(target_duration, "between 30 and 60")

    system_prompt = (
        f"You are an expert viral TikTok clipping AI agent. "
        f"Analyse the transcript of a video spoken in '{video_language}'. "
        f"Identify EXACTLY {max_clips} distinct and non-overlapping segments with {objective_desc}. "
        f"You must strive to find all {max_clips} segments unless the video is far too short. "
        f"Each segment must be {duration_desc} seconds long. "
        f"Return only segments with exact second timestamps. "
        f"Write all titles and justifications in the same language as the transcript."
    )

    llm = ChatGroq(
        model=settings.LLMMODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.4,
    )
    structured_llm = llm.with_structured_output(ViralMomentsResponse)
    messages = [("system", system_prompt), ("human", transcript)]
    result: ViralMomentsResponse = await structured_llm.ainvoke(messages)
    logger.info("Extracted %d viral moments.", len(result.momentos))
    return [m.model_dump() for m in result.momentos]
