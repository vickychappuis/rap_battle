"""Agent prompt templates for the rap battle."""

from .persona import (
    MAX_AGE,
    MAX_PERSONA_BLOCK_CHARS,
    MIN_AGE,
    PERSONA_FIELD_LIMITS,
    build_persona_data_block,
    sanitize_prompt_text,
)
from .lyricist_prompt import (
    LYRICIST_PROMPT_TEMPLATE,
    NO_PERSONA_BLOCK,
    TURN_INSTRUCTIONS,
    TurnData,
    build_battle_context,
    build_opponent_persona_block,
    build_turn_instructions,
)
from .judge_prompt import build_judge_system_prompt, build_judge_transcript

__all__ = [
    "LYRICIST_PROMPT_TEMPLATE",
    "MAX_AGE",
    "MAX_PERSONA_BLOCK_CHARS",
    "MIN_AGE",
    "NO_PERSONA_BLOCK",
    "PERSONA_FIELD_LIMITS",
    "TURN_INSTRUCTIONS",
    "TurnData",
    "build_battle_context",
    "build_judge_system_prompt",
    "build_judge_transcript",
    "build_opponent_persona_block",
    "build_persona_data_block",
    "build_turn_instructions",
    "sanitize_prompt_text",
]
