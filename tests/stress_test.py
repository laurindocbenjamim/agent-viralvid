# -*- coding: utf-8 -*-
"""Stress and load tests: concurrent ASGI request volumes with mocked dependencies."""

import asyncio
import time
import httpx
import pytest
from unittest.mock import patch

from backend.app.main import app


@pytest.mark.asyncio
async def test_concurrent_session_creation_stress():
    """Simulate 50 parallel anonymous session requests.

    Verifies that token generation and cookie setting handles concurrency
    without bottlenecks. Average per-request latency must remain under 250ms.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        start = time.perf_counter()

        async def create_session():
            res = await client.post("/api/auth/session")
            return res.status_code, res.elapsed.total_seconds()

        results = await asyncio.gather(*[create_session() for _ in range(50)])
        total = time.perf_counter() - start

        codes = [r[0] for r in results]
        latencies = [r[1] for r in results]
        avg = sum(latencies) / len(latencies)

        assert all(c == 200 for c in codes), f"Failed statuses: {codes}"
        assert avg < 0.25, f"Avg latency too high: {avg:.4f}s"
        print(f"\n[STRESS] 50 sessions in {total:.3f}s — avg {avg*1000:.1f}ms/req")


@pytest.mark.asyncio
@patch("backend.app.clipper.routes.process_video_pipeline")
@patch("backend.app.clipper.routes.set_task_status")
@patch("backend.app.clipper.routes.save_sqlite_task")
async def test_concurrent_submission_stress(mock_sqlite, mock_status, mock_pipeline):
    """Simulate 30 parallel authenticated submission requests.

    Verifies input validation and background task registration under load.
    All requests must return HTTP 202 Accepted.
    """
    mock_status.return_value = None
    mock_sqlite.return_value = None
    mock_pipeline.return_value = None

    from backend.app.auth.security import create_access_token
    token = create_access_token({"sub": "stress-session"})

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("access_token", token)

        async def submit():
            return (await client.post("/api/clipper/submit", json={
                "video_source": "https://www.youtube.com/watch?v=kwEtOyaFhCA",
                "video_language": "pt-BR",
            })).status_code

        codes = await asyncio.gather(*[submit() for _ in range(30)])
        assert all(c == 202 for c in codes), f"Failed: {codes}"
        print(f"\n[STRESS] 30 concurrent submissions — all 202 OK")
