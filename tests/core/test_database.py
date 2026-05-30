# -*- coding: utf-8 -*-
"""Integration tests for the core database layer: Upstash REST and SQLite helpers."""

import json
import os
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

TEST_DB = "test_viralvid_core.db"


@pytest.mark.asyncio
async def test_set_and_get_status_upstash():
    """Verify set_task_status and get_task_status call Upstash REST correctly."""
    from backend.app.core import database as db

    mock_upstash = AsyncMock(return_value="OK")
    with patch.object(db, "_use_upstash", True), \
         patch.object(db, "_upstash", mock_upstash):
        await db.set_task_status("task-001", "Baixando")
        mock_upstash.assert_called_with(["SET", "status:task-001", "Baixando"])

    mock_upstash2 = AsyncMock(return_value="Baixando")
    with patch.object(db, "_use_upstash", True), \
         patch.object(db, "_upstash", mock_upstash2):
        result = await db.get_task_status("task-001")
        assert result == "Baixando"
        mock_upstash2.assert_called_with(["GET", "status:task-001"])


@pytest.mark.asyncio
async def test_cache_and_get_results_upstash():
    """Verify cache_results and get_cached_results call Upstash REST correctly."""
    from backend.app.core import database as db

    clips = '[{"clip_id": 1}]'
    mock_set = AsyncMock(return_value="OK")
    with patch.object(db, "_use_upstash", True), \
         patch.object(db, "_upstash", mock_set):
        await db.cache_results("task-001", clips)
        mock_set.assert_called_with(["SET", "result:task-001", clips])

    mock_get = AsyncMock(return_value=clips)
    with patch.object(db, "_use_upstash", True), \
         patch.object(db, "_upstash", mock_get):
        result = await db.get_cached_results("task-001")
        assert result == clips


@pytest.mark.asyncio
async def test_sqlite_full_lifecycle():
    """Verify SQLite task creation, status update, and result persistence."""
    from backend.app.core import database as db

    with patch.object(db, "SQLITE_DB_PATH", TEST_DB):
        await db.init_sqlite_db()
        assert os.path.exists(TEST_DB)

        await db.save_sqlite_task(
            "task-999", "session-abc", "https://yt.com/x", "Baixando"
        )
        with sqlite3.connect(TEST_DB) as conn:
            row = conn.execute(
                "SELECT user_id, video_url, status FROM tasks WHERE task_id = ?",
                ("task-999",),
            ).fetchone()
        assert row == ("session-abc", "https://yt.com/x", "Baixando")

        await db.save_sqlite_task_results("task-999", "Concluido", '[{"clip_id": 1}]')
        with sqlite3.connect(TEST_DB) as conn:
            row = conn.execute(
                "SELECT status, results FROM tasks WHERE task_id = ?",
                ("task-999",),
            ).fetchone()
        assert row[0] == "Concluido"
        assert row[1] == '[{"clip_id": 1}]'

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
