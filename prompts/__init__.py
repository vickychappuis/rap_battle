"""Agent prompt templates for the rap battle."""

from .lyricist_prompt import (
    LYRICIST_PROMPT_TEMPLATE,
    TURN_INSTRUCTIONS,
    TurnData,
    build_battle_context,
)
from .judge_prompt import build_judge_system_prompt, build_judge_transcript

__all__ = [
    "LYRICIST_PROMPT_TEMPLATE",
    "TURN_INSTRUCTIONS",
    "TurnData",
    "build_battle_context",
    "build_judge_system_prompt",
    "build_judge_transcript",
]
