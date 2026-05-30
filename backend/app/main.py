# -*- coding: utf-8 -*-
"""FastAPI monolith entry point: assembles all bounded context routers."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.auth.routes import router as auth_router
from backend.app.clipper.routes import router as clipper_router
from backend.app.core.database import init_sqlite_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ViralVid AI Clipper",
    description="Automated viral TikTok clip generator with AI-powered moment extraction.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static clip output directory for video previewing
clips_path = Path("./backend/clips")
clips_path.mkdir(parents=True, exist_ok=True)
app.mount("/clips", StaticFiles(directory=str(clips_path)), name="clips")

# Register bounded context routers
app.include_router(auth_router)
app.include_router(clipper_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialise infrastructure on application startup."""
    await init_sqlite_db()
    logger.info("ViralVid AI Clipper v2.0.0 is ready.")


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the single-page frontend application.

    Returns:
        FileResponse: The main index.html dashboard.
    """
    return FileResponse("backend/app/static/index.html")
