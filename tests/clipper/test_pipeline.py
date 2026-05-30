# -*- coding: utf-8 -*-
"""Unit tests for the clipper pipeline: LLM extraction and Pydantic schema."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.clipper.pipeline import (
    ViralMoment,
    ViralMomentsResponse,
    extract_viral_moments,
)


def test_viral_moment_model_validates_correctly():
    """ViralMoment accepts valid field values."""
    m = ViralMoment(id=1, inicio_segundos=10, fim_segundos=45, titulo="Hook", justificativa="Strong.")
    assert m.inicio_segundos == 10
    assert m.fim_segundos == 45


def test_viral_moment_rejects_negative_start():
    """ViralMoment should reject negative start timestamps."""
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        ViralMoment(id=1, inicio_segundos=-5, fim_segundos=30, titulo="X", justificativa="Y")


@pytest.mark.asyncio
async def test_extract_viral_moments_returns_dicts():
    """extract_viral_moments should return a list of serialised moment dicts."""
    mock_moments = [
        ViralMoment(id=1, inicio_segundos=5, fim_segundos=35, titulo="Gancho", justificativa="Forte."),
        ViralMoment(id=2, inicio_segundos=60, fim_segundos=90, titulo="Revelação", justificativa="Impacto."),
    ]
    mock_response = ViralMomentsResponse(momentos=mock_moments)

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

    with patch("backend.app.clipper.pipeline.ChatGroq", return_value=mock_llm):
        result = await extract_viral_moments(
            transcript="Teste de transcrição.",
            video_language="pt-BR",
            clip_objective="Viral/Engraçado",
            target_duration="30-60",
            max_clips=2,
        )

    assert len(result) == 2
    assert result[0]["titulo"] == "Gancho"
    assert result[1]["inicio_segundos"] == 60
