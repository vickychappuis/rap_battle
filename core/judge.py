"""Battle judging: an OpenAI chat model scores the finished battle.

Domain logic, like the lyricist in `core/generation.py` - the API pipeline
only wires session state into `judge_battle` and stores the verdict.
"""

import json
import logging
import os
from typing import Mapping, Optional, Tuple

import openai

from core.prompts.judge_prompt import build_judge_system_prompt, build_judge_transcript

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
JUDGE_MAX_ATTEMPTS = 3

DRAW_VERDICT = ("draw", "The judge couldn't decide — it's a draw!")


def judge_battle(
    turn_history,
    opponent_name: str,
    opponent_persona: Optional[Mapping] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """Judge a finished battle and return ``(winner, reason)``.

    ``winner`` is ``"user"`` or ``"ai"``; after ``JUDGE_MAX_ATTEMPTS`` failed
    calls the battle is declared a draw rather than erroring out - a missing
    verdict should never eat an otherwise completed battle.
    """
    client = openai.OpenAI(api_key=api_key)

    transcript = build_judge_transcript(turn_history, opponent_name)
    messages = [
        {
            "role": "system",
            "content": build_judge_system_prompt(opponent_name, opponent_persona),
        },
        {"role": "user", "content": transcript},
    ]

    # Its own env var on purpose: the judge is a plain chat-completions call,
    # while OPENAI_MODEL drives the gpt-5-family reasoning lyricist.
    judge_model = os.environ.get("OPENAI_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)

    for attempt in range(1, JUDGE_MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=judge_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            result_text = response.choices[0].message.content or "{}"
            result = json.loads(result_text)
            winner = result.get("winner", "")
            if winner not in ("user", "ai"):
                raise ValueError(f"Invalid winner value: '{winner}'")
            logger.info("Judge decision: %s", winner)
            return winner, result.get("reason", "")
        except Exception as e:
            logger.warning(
                "Judge attempt %d/%d failed: %s", attempt, JUDGE_MAX_ATTEMPTS, e
            )

    return DRAW_VERDICT
