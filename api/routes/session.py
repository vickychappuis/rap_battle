"""Session routes for the rap battle API."""

import math
import os
import uuid
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from api.models.session import (
    SessionCreate,
    SessionResponse,
    SessionStatus,
    PipelineStep,
    TurnData,
)
from api.services.pipeline import (
    MAX_TURN_RETRIES,
    SessionState,
    cleanup_expired,
    sessions,
    pipeline_service,
)

router = APIRouter(prefix="/api/session", tags=["session"])

# Configuration from environment
BPM = int(os.environ.get("BPM", 90))
BARS_PER_TURN = int(os.environ.get("BARS_PER_TURN", 16))
TURNS_PER_PLAYER = int(os.environ.get("TURNS_PER_PLAYER", 2))

# Maximum size of one uploaded recording. A ~60s browser recording is
# Opus/WebM at ~32kbps (~250KB); 8MB leaves generous room for Safari's
# mp4/AAC while capping what a single request can make us buffer.
# Configurable via MAX_UPLOAD_MB.
MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", 8))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)
UPLOAD_CHUNK_BYTES = 256 * 1024

# GLOBAL rate limiting - these counters are shared by ALL callers, not
# per-user (there are no accounts in this POC). 4 battles/hour and 15/day is
# a spend cap for the whole deployment, which also means a single abuser can
# lock everyone out until the window rolls over.
RATE_LIMIT_HOURLY = 4
RATE_LIMIT_DAILY = 15
_session_timestamps: list[float] = []


def _check_rate_limit() -> str | None:
    now = time.time()
    hour_ago = now - 3600
    day_ago = now - 86400

    # Prune old entries
    _session_timestamps[:] = [t for t in _session_timestamps if t > day_ago]

    hourly = sum(1 for t in _session_timestamps if t > hour_ago)
    daily = len(_session_timestamps)

    if hourly >= RATE_LIMIT_HOURLY:
        return "Rate limit exceeded: max 4 battles per hour. Try again later."
    if daily >= RATE_LIMIT_DAILY:
        return "Rate limit exceeded: max 15 battles per day. Try again tomorrow."
    return None


@router.post("", response_model=SessionResponse)
async def create_session(body: SessionCreate = SessionCreate()):
    """
    Create a new battle session with global rate limiting.

    Returns session config including BPM, bars per turn, and base track URL.
    """
    limit_msg = _check_rate_limit()
    if limit_msg:
        raise HTTPException(status_code=429, detail=limit_msg)

    # Nothing else reclaims memory or generated mp3s, so sweep on create.
    cleanup_expired()

    _session_timestamps.append(time.time())

    session_id = str(uuid.uuid4())

    # Resolve the AI MC's identity. The persona's own name wins when present;
    # `opponent_name` alone keeps working for clients that send nothing else.
    # Both have already been length-capped and sanitised by SessionCreate.
    persona = body.opponent
    opponent_name = (persona.name if persona else None) or body.opponent_name
    persona_data = None
    if persona is not None:
        persona_data = persona.model_dump()
        persona_data["name"] = opponent_name

    # Create session state
    session = SessionState(
        session_id=session_id,
        bpm=BPM,
        bars_per_turn=BARS_PER_TURN,
        turns_per_player=TURNS_PER_PLAYER,
        opponent_name=opponent_name or "the challenger",
        opponent_persona=persona_data,
    )
    sessions[session_id] = session

    return SessionResponse(
        session_id=session_id,
        bpm=BPM,
        bars_per_turn=BARS_PER_TURN,
        turns_per_player=TURNS_PER_PLAYER,
        # Rounded UP: core.generation also ceils the ElevenLabs duration, so
        # the user's record window and the AI's verse cover the same whole
        # number of seconds (16 bars @90bpm = 42.67s -> 43s on both sides).
        record_duration=math.ceil(session.seconds),
        max_turn_retries=MAX_TURN_RETRIES,
        base_track_url="/static/tracks/base_90bpm.mp3",
    )


@router.post("/{session_id}/recording")
async def upload_recording(session_id: str, audio: UploadFile = File(...)):
    """
    Upload recorded audio blob (WebM/MP4).

    Saves to temp file and starts the pipeline processing.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session.touch()

    # Allow recording in IDLE state (first turn) or AWAITING_USER state (subsequent turns)
    if session.step not in (PipelineStep.IDLE, PipelineStep.AWAITING_USER):
        raise HTTPException(
            status_code=400,
            detail=f"Session not ready for recording (step: {session.step})"
        )

    # Reject oversized uploads up front when the client declares a length.
    declared_length = audio.size
    if declared_length is not None and declared_length > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Recording too large (max {MAX_UPLOAD_MB:g}MB)",
        )

    # Determine file extension from content type
    content_type = audio.content_type or ""
    if "webm" in content_type:
        suffix = ".webm"
    elif "mp4" in content_type or "m4a" in content_type:
        suffix = ".mp4"
    else:
        suffix = ".webm"  # Default to webm

    # Save uploaded file to temp location
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    # Stream to disk in chunks so an oversized (or lying) client can never
    # make us buffer an unbounded body in memory.
    try:
        written = 0
        with open(temp_path, "wb") as f:
            while chunk := await audio.read(UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise ValueError("too_large")
                f.write(chunk)
    except ValueError:
        Path(temp_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"Recording too large (max {MAX_UPLOAD_MB:g}MB)",
        )
    except Exception as e:
        Path(temp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {e}")

    # Start pipeline processing in background. `start_pipeline` clears the
    # previous turn's data and flips the session into a busy step.
    if not pipeline_service.start_pipeline(session, temp_path):
        Path(temp_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail="A turn is already being processed for this session",
        )

    return {"status": "processing", "current_turn": session.current_turn}


@router.post("/{session_id}/retry")
async def retry_turn(session_id: str):
    """
    Retry the current turn after an error.

    Only available when session is in ERROR state.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session.touch()

    if session.step != PipelineStep.ERROR:
        raise HTTPException(
            status_code=400,
            detail="Can only retry after error"
        )

    if session.retry_count >= MAX_TURN_RETRIES:
        raise HTTPException(
            status_code=400,
            detail="Maximum retries exceeded. Please start over."
        )

    # The pipeline resumes from the first unfinished stage, so the recording
    # is only needed when transcription itself has not succeeded yet.
    needs_audio = session.transcription is None
    if needs_audio and not (session.audio_path and Path(session.audio_path).exists()):
        session.step = PipelineStep.AWAITING_USER
        return {"status": "need_rerecord", "message": "Audio file expired. Please record again."}

    # Clear error and resume the pipeline where it left off.
    session.error = None

    if not pipeline_service.resume_pipeline(session):
        # A retry is already running (double click / double request).
        raise HTTPException(
            status_code=409,
            detail="A retry is already in progress for this session",
        )

    return {"status": "retrying", "retry_count": session.retry_count}


@router.get("/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """
    Poll session processing status.

    Returns current step, turn info, and any available results.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session.touch()

    return SessionStatus(
        step=session.step,
        timing=session.timing,
        current_turn=session.current_turn,
        turns_per_player=session.turns_per_player,
        turn_history=session.turn_history,
        transcription=session.transcription,
        lyrics=session.lyrics,
        ai_audio_url=session.ai_audio_url,
        error=session.error,
        retry_count=session.retry_count,
        winner=session.winner,
        judge_reason=session.judge_reason,
    )
