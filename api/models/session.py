"""Pydantic models for session management."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class PipelineStep(str, Enum):
    """Pipeline processing steps."""
    IDLE = "idle"
    AWAITING_USER = "awaiting_user"  # Waiting for user to record
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    GENERATING_LYRICS = "generating_lyrics"
    GENERATING_AUDIO = "generating_audio"
    PLAYING_RESPONSE = "playing_response"
    JUDGING = "judging"
    COMPLETE = "complete"
    ERROR = "error"


class TurnData(BaseModel):
    """Data for a single turn in the battle."""
    turn_number: int
    player: str  # "user" | "ai"
    transcription: Optional[str] = None  # User turns
    lyrics: Optional[str] = None  # AI turns
    audio_url: Optional[str] = None  # AI turns
    timing: Optional[dict] = None  # Timing data for AI turns


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    pass  # No parameters needed for POC


class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    bpm: int
    bars_per_turn: int
    turns_per_player: int
    record_duration: int
    base_track_url: str


class SessionStatus(BaseModel):
    """Response model for session status polling."""
    step: PipelineStep
    current_turn: int
    turns_per_player: int
    turn_history: List[TurnData]
    transcription: Optional[str] = None
    lyrics: Optional[str] = None
    ai_audio_url: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    timing: Optional[dict] = None  # Timing data for current turn
    winner: Optional[str] = None
    judge_reason: Optional[str] = None
