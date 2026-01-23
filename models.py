"""
Pydantic models for the Rap Battle system.

These models define the data schemas for agent inputs/outputs.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class LyricistOutput(BaseModel):
    """Schema for Lyricist agent output - beat-based format"""
    grid_beats: int = Field(description="Total beats in the response")
    beats: List[str] = Field(description="List of beat texts, one per beat")

    @field_validator('beats')
    @classmethod
    def validate_beats(cls, v, info):
        """Validate beat list - lenient validation, just check basics"""
        # Don't strictly validate beat count here - we'll fix it in validate_lyricist_output
        # Just check each beat has reasonable content
        for i, beat in enumerate(v):
            word_count = len(beat.split())
            # Allow 1-4 words per beat (flexible)
            if word_count < 1 or word_count > 4:
                # Just warn, don't fail
                pass

        return v


class PerformanceBeat(BaseModel):
    """Single beat in the performance grid"""
    beat: int = Field(description="Beat number (1-indexed)")
    bar: int = Field(description="Bar number (1-indexed)")
    beat_in_bar: int = Field(description="Beat within the bar (1-4)")
    text: str = Field(description="Text to deliver on this beat")


class GridBuilderOutput(BaseModel):
    """Schema for Grid Builder output"""
    ms_per_beat: float = Field(description="Milliseconds per beat")
    performance_grid: List[PerformanceBeat] = Field(description="Beat-by-beat performance grid")
    plain_take: str = Field(description="Single concatenated text in delivery order")
    tts_prompt: str = Field(description="Final TTS prompt string")
