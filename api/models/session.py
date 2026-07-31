"""Pydantic models for session management."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from core.prompts.persona import (
    MAX_AGE,
    MAX_PERSONA_BLOCK_CHARS,
    MIN_AGE,
    PERSONA_FIELD_LIMITS,
    sanitize_prompt_text,
)


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


class OpponentPersona(BaseModel):
    """Client-supplied character sheet for the AI MC.

    UNTRUSTED. `POST /api/session` accepts any JSON body from anyone, so the
    frontend's OPPONENTS list is not a constraint on what arrives here. Each
    field caps the RAW value (over-length input is rejected with a 422) and is
    then sanitised down to a single harmless line before it can reach a prompt.
    Unknown keys (`id`, `imageSrc`, ...) are ignored rather than carried along.
    """
    name: Optional[str] = Field(default=None, max_length=PERSONA_FIELD_LIMITS["name"])
    age: Optional[int] = Field(default=None, ge=MIN_AGE, le=MAX_AGE)
    claims: Optional[str] = Field(default=None, max_length=PERSONA_FIELD_LIMITS["claims"])
    reality: Optional[str] = Field(default=None, max_length=PERSONA_FIELD_LIMITS["reality"])
    extra_info: Optional[str] = Field(
        default=None, max_length=PERSONA_FIELD_LIMITS["extra_info"]
    )

    @field_validator("name", "claims", "reality", "extra_info")
    @classmethod
    def _sanitize(cls, value: Optional[str], info) -> Optional[str]:
        if value is None:
            return None
        # Runs after the max_length constraint, so this only ever shortens a
        # value that was already within its cap.
        return sanitize_prompt_text(value, PERSONA_FIELD_LIMITS[info.field_name]) or None

    @model_validator(mode="after")
    def _cap_total_size(self) -> "OpponentPersona":
        total = sum(
            len(v)
            for v in (self.name, self.claims, self.reality, self.extra_info)
            if v
        )
        if total > MAX_PERSONA_BLOCK_CHARS:
            raise ValueError(
                f"opponent persona too long: {total} characters across all fields "
                f"(max {MAX_PERSONA_BLOCK_CHARS})"
            )
        return self


class SessionCreate(BaseModel):
    """Request model for creating a new session.

    Both fields are optional: a body of `{}` or a bare `opponent_name` is still
    a valid request, and the battle then runs without a persona.
    """
    opponent_name: Optional[str] = Field(
        default=None, max_length=PERSONA_FIELD_LIMITS["name"]
    )
    opponent: Optional[OpponentPersona] = None

    @field_validator("opponent_name")
    @classmethod
    def _sanitize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return sanitize_prompt_text(value, PERSONA_FIELD_LIMITS["name"]) or None


class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    bpm: int
    bars_per_turn: int
    turns_per_player: int
    record_duration: int
    # The turn retry budget, so the frontend never has to hardcode a mirror
    # of the backend's MAX_TURN_RETRIES.
    max_turn_retries: int
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
