# -*- coding: utf-8 -*-
"""Clipper bounded context: AI viral moment extraction via LangChain + Groq."""

import logging
from typing import List

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class SubtitlePhrase(BaseModel):
    """A single timed subtitle phrase for dynamic caption rendering."""

    text: str = Field(..., description="The subtitle text for this phrase (1-6 words, highlighting key words).")
    start_offset: float = Field(..., ge=0, description="Start offset in seconds relative to clip start.")
    end_offset: float = Field(..., ge=0.1, description="End offset in seconds relative to clip start.")


class ViralMoment(BaseModel):
    """Schema for a single AI-identified viral video segment."""

    id: int = Field(..., description="Ordered index of the clip.")
    inicio_segundos: int = Field(..., ge=0, description="Start timestamp in seconds.")
    fim_segundos: int = Field(..., ge=1, description="End timestamp in seconds.")
    titulo: str = Field(..., description="High-impact TikTok hook title.")
    justificativa: str = Field(..., description="Why this moment is viral.")
    legendas: List[SubtitlePhrase] = Field(
        default_factory=list,
        description="Timed subtitle phrases covering the full clip duration. "
                    "Each phrase is 1-6 words highlighting important words from the transcript.",
    )


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
    """Extract viral clip moments from a video transcript using the Groq LLM with fallbacks.

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
        f"Write all titles, justifications, and subtitles in the same language as the transcript.\n\n"
        f"For each segment, you MUST also provide 'legendas' — a list of timed subtitle phrases "
        f"that cover the ENTIRE clip duration from start to end. Rules for legendas:\n"
        f"- Each phrase must be 1 to 6 words, highlighting the most important or impactful words.\n"
        f"- Phrases must be chronologically ordered and cover the full duration with no large gaps.\n"
        f"- start_offset is relative to the clip start (0 = beginning of clip).\n"
        f"- end_offset must be slightly after start_offset (at least 0.5s per phrase).\n"
        f"- Aim for roughly 2-4 seconds per phrase, adapting to the transcript pacing.\n"
        f"- Use UPPERCASE for emphasis words that are key to the message."
    )

    # Candidates to try: primary configured model first, then standard reliable fallbacks
    models_to_try = [settings.LLMMODEL, "llama-3.3-70b-specdec", "llama3-8b-8192"]
    models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))  # unique, preserve order

    last_exc = None
    for model_name in models_to_try:
        try:
            logger.info("Attempting viral moment extraction with Groq model: %s", model_name)
            llm = ChatGroq(
                model=model_name,
                api_key=settings.GROQ_API_KEY,
                temperature=0.4,
                timeout=30.0,  # Prevent indefinite hangs
            )
            structured_llm = llm.with_structured_output(ViralMomentsResponse)
            messages = [("system", system_prompt), ("human", transcript)]
            result: ViralMomentsResponse = await structured_llm.ainvoke(messages)
            logger.info("Successfully extracted %d viral moments using %s", len(result.momentos), model_name)
            return [m.model_dump() for m in result.momentos]
        except Exception as exc:
            logger.warning("Failed structured extraction with model %s: %s. Trying next...", model_name, exc)
            last_exc = exc

    raise last_exc or Exception("All configured LLM models failed to extract viral moments.")

