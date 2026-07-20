"""
FastAPI application for the rap battle frontend.

Provides REST API endpoints and serves static files.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from api.routes import session_router

app = FastAPI(
    title="Rap Battle API",
    description="Backend API for the rap battle frontend",
    version="0.1.0",
)

_extra_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)

api_dir = Path(__file__).parent
project_root = api_dir.parent

# Generated audio (created on demand); served back to the frontend.
static_generated_dir = api_dir / "static" / "generated"
static_generated_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/generated", StaticFiles(directory=str(static_generated_dir)), name="generated")

# Base instrumental tracks.
tracks_dir = project_root / "assets" / "tracks"
if tracks_dir.exists():
    app.mount("/static/tracks", StaticFiles(directory=str(tracks_dir)), name="tracks")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
