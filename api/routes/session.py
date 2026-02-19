"""Session routes for the rap battle API."""

import os
import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from typing import Optional

from api.routes.access import is_valid_invite_code
from api.models.session import (
    SessionResponse,
    SessionStatus,
    PipelineStep,
    TurnData,
)
from api.services.pipeline import (
    SessionState,
    sessions,
    pipeline_service,
)

router = APIRouter(prefix="/api/session", tags=["session"])

# Configuration from environment
BPM = int(os.environ.get("BPM", 90))
BARS_PER_TURN = int(os.environ.get("BARS_PER_TURN", 16))
TURNS_PER_PLAYER = int(os.environ.get("TURNS_PER_PLAYER", 2))


@router.post("", response_model=SessionResponse)
async def create_session(x_invite_code: Optional[str] = Header(None)):
    """
    Create a new battle session. Requires a valid invite code.

    Returns session config including BPM, bars per turn, and base track URL.
    """
    if not x_invite_code or not is_valid_invite_code(x_invite_code):
        raise HTTPException(status_code=401, detail="Invalid invite code")

    session_id = str(uuid.uuid4())

    # Calculate record duration from bars and BPM
    grid_beats = BARS_PER_TURN * 4
    seconds = grid_beats * (60 / BPM)
    record_duration = int(seconds)  # seconds

    # Create session state
    session = SessionState(
        session_id=session_id,
        bpm=BPM,
        bars_per_turn=BARS_PER_TURN,
        turns_per_player=TURNS_PER_PLAYER,
    )
    sessions[session_id] = session

    return SessionResponse(
        session_id=session_id,
        bpm=BPM,
        bars_per_turn=BARS_PER_TURN,
        turns_per_player=TURNS_PER_PLAYER,
        record_duration=record_duration,
        base_track_url="/static/tracks/base_90bpm.wav",
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

    # Allow recording in IDLE state (first turn) or AWAITING_USER state (subsequent turns)
    if session.step not in (PipelineStep.IDLE, PipelineStep.AWAITING_USER):
        raise HTTPException(
            status_code=400,
            detail=f"Session not ready for recording (step: {session.step})"
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

    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)
    except Exception as e:
        Path(temp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {e}")

    # Clear previous turn data before starting new pipeline
    session.clear_current_turn_data()

    # Start pipeline processing in background
    session.step = PipelineStep.RECORDING  # Brief transition state
    pipeline_service.start_pipeline(session, temp_path)

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

    if session.step != PipelineStep.ERROR:
        raise HTTPException(
            status_code=400,
            detail="Can only retry after error"
        )

    if session.retry_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Maximum retries exceeded. Please start over."
        )

    # Clear error and restart pipeline with existing audio path
    session.error = None

    # If we still have the audio path, reuse it
    if session.audio_path and Path(session.audio_path).exists():
        pipeline_service.start_pipeline(session, session.audio_path)
        return {"status": "retrying", "retry_count": session.retry_count}
    else:
        # Audio was cleaned up, need to re-record
        session.step = PipelineStep.AWAITING_USER
        return {"status": "need_rerecord", "message": "Audio file expired. Please record again."}


@router.get("/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """
    Poll session processing status.

    Returns current step, turn info, and any available results.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    return SessionStatus(
        step=session.step,
        current_turn=session.current_turn,
        turns_per_player=session.turns_per_player,
        turn_history=session.turn_history,
        transcription=session.transcription,
        lyrics=session.lyrics,
        ai_audio_url=session.ai_audio_url,
        error=session.error,
        retry_count=session.retry_count,
    )
