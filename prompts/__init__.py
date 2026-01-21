"""
Prompts package for Rap Battle AI

Contains all agent prompt templates.
Each agent has its own prompt file.
"""

from .lyricist_prompt import (
    LYRICIST_PROMPT_TEMPLATE,
    LYRICIST_METADATA,
    TURN_INSTRUCTIONS,
    TurnData,
    build_battle_context,
)
from .grid_builder_prompt import GRID_BUILDER_PROMPT_TEMPLATE, GRID_BUILDER_METADATA

PROMPT_METADATA = {
    "lyricist": LYRICIST_METADATA,
    "grid_builder": GRID_BUILDER_METADATA
}

__all__ = [
    "LYRICIST_PROMPT_TEMPLATE",
    "GRID_BUILDER_PROMPT_TEMPLATE",
    "LYRICIST_METADATA",
    "GRID_BUILDER_METADATA",
    "PROMPT_METADATA",
    "TURN_INSTRUCTIONS",
    "TurnData",
    "build_battle_context",
]
