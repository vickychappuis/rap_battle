"""
Pydantic models for the Rap Battle system.

These models define the data schemas for agent inputs/outputs.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class LyricistOutput(BaseModel):
    """Schema for Lyricist agent output - bar-based format"""
    bars: List[str] = Field(description="List of rap bars (lines), one per bar")
    mood_arc: str = Field(
        default="confident",
        description="Mood arc description, e.g. 'confident -> mocking -> aggressive'"
    )

    @field_validator('bars')
    @classmethod
    def validate_bars(cls, v, info):
        """Validate bar list - lenient validation, just check basics"""
        for i, bar in enumerate(v):
            if not bar.strip():
                raise ValueError(f"Bar {i+1} is empty")
        return v


class GridBuilderOutput(BaseModel):
    """Schema for Grid Builder output"""
    ms_per_beat: float = Field(description="Milliseconds per beat")
    plain_take: str = Field(description="All bars joined as a single text block")
    tts_prompt: str = Field(description="Final TTS prompt string")
