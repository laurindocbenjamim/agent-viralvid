# -*- coding: utf-8 -*-
"""Core database layer: Upstash Redis REST API + SQLite persistence."""

import asyncio
import json
import logging
import sqlite3
from typing import Optional

import httpx
import redis.asyncio as aioredis

from backend.app.core.config import settings

logger = logging.getLogger(__name__)
SQLITE_DB_PATH = "tiktok_clipper.db"

# ---------------------------------------------------------------------------
# Redis client — Upstash REST when credentials present, else standard redis://
# ---------------------------------------------------------------------------
_upstash_url = settings.UPSTASH_REDIS_REST_URL.rstrip("/")
_upstash_token = settings.UPSTASH_REDIS_REST_TOKEN
_use_upstash = bool(_upstash_url and _upstash_token)

if _use_upstash:
    logger.info("Using Upstash Redis REST API at %s", _upstash_url)
else:
    redis_client: aioredis.Redis = aioredis.from_url(
        settings.REDIS_URL, decode_responses=True
    )


async def _upstash(command: list) -> Optional[str]:
    """Execute a Redis command via the Upstash REST API.

    Args:
        command (list): Redis command tokens e.g. ["SET", "key", "value"].

    Returns:
        Optional[str]: The 'result' field from the Upstash JSON response.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _upstash_url,
            headers={"Authorization": f"Bearer {_upstash_token}"},
            json=command,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("result")


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Return the standard async Redis client (None when Upstash REST is used).

    Returns:
        Optional[aioredis.Redis]: Client instance or None for Upstash mode.
    """
    return None if _use_upstash else redis_client  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Task status helpers
# ---------------------------------------------------------------------------
async def set_task_status(task_id: str, status: str) -> None:
    """Persist task progress status to Redis or Upstash.

    Args:
        task_id (str): Unique task identifier.
        status (str): Progress label e.g. "Baixando", "Renderizando".
    """
    if _use_upstash:
        await _upstash(["SET", f"status:{task_id}", status])
    else:
        await redis_client.set(f"status:{task_id}", status)  # type: ignore[name-defined]


async def get_task_status(task_id: str) -> Optional[str]:
    """Read task progress status from Redis or Upstash.

    Args:
        task_id (str): Unique task identifier.

    Returns:
        Optional[str]: Status string or None if not found.
    """
    if _use_upstash:
        result = await _upstash(["GET", f"status:{task_id}"])
        return result if isinstance(result, str) else None
    return await redis_client.get(f"status:{task_id}")  # type: ignore[name-defined]


async def cache_results(task_id: str, results_json: str) -> None:
    """Store final clip metadata in Redis or Upstash for fast polling.

    Args:
        task_id (str): Unique task identifier.
        results_json (str): Serialised JSON string of clip metadata.
    """
    if _use_upstash:
        await _upstash(["SET", f"result:{task_id}", results_json])
    else:
        await redis_client.set(f"result:{task_id}", results_json)  # type: ignore[name-defined]


async def get_cached_results(task_id: str) -> Optional[str]:
    """Retrieve cached clip metadata from Redis or Upstash.

    Args:
        task_id (str): Unique task identifier.

    Returns:
        Optional[str]: Serialised JSON string or None.
    """
    if _use_upstash:
        result = await _upstash(["GET", f"result:{task_id}"])
        return result if isinstance(result, str) else None
    return await redis_client.get(f"result:{task_id}")  # type: ignore[name-defined]


# ---------------------------------------------------------------------------
# SQLite schema initialisation
# ---------------------------------------------------------------------------
def _init_schema() -> None:
    """Create all required SQLite tables if they do not exist (synchronous)."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id    TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                video_url  TEXT NOT NULL,
                status     TEXT NOT NULL,
                results    TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


async def init_sqlite_db() -> None:
    """Asynchronously initialise the SQLite schema on application startup."""
    logger.info("Initialising SQLite schema...")
    await asyncio.to_thread(_init_schema)


# ---------------------------------------------------------------------------
# SQLite durability helpers
# ---------------------------------------------------------------------------
def _upsert_task(task_id: str, user_id: str, video_url: str, status: str) -> None:
    """Insert or update a task row in SQLite synchronously."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO tasks (task_id, user_id, video_url, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET status = excluded.status
            """,
            (task_id, user_id, video_url, status),
        )
        conn.commit()


async def save_sqlite_task(
    task_id: str, user_id: str, video_url: str, status: str
) -> None:
    """Durably persist a task record in SQLite.

    Args:
        task_id (str): Unique task identifier.
        user_id (str): Session identifier from the cookie token.
        video_url (str): Sanitised video source URL.
        status (str): Current pipeline status label.
    """
    await asyncio.to_thread(_upsert_task, task_id, user_id, video_url, status)


def _save_results(task_id: str, status: str, results_json: str) -> None:
    """Update the final status and results in SQLite synchronously."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, results = ? WHERE task_id = ?",
            (status, results_json, task_id),
        )
        conn.commit()


async def save_sqlite_task_results(
    task_id: str, status: str, results_json: str
) -> None:
    """Durably persist the final rendering results in SQLite.

    Args:
        task_id (str): Unique task identifier.
        status (str): Final status string ("Concluido" or "Erro: ...").
        results_json (str): Serialised clip metadata JSON string.
    """
    await asyncio.to_thread(_save_results, task_id, status, results_json)
