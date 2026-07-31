"""Lyric generation and audio synthesis helpers.

Shared by the API pipeline:
- Lyricist agent (LangChain + OpenAI) that writes timed battle bars
- Output validation
- ElevenLabs music generation
"""

import logging
import math
import os
from pathlib import Path

import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from core.models import LyricistOutput
from core.prompts import LYRICIST_PROMPT_TEMPLATE

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/music/detailed"

logger = logging.getLogger(__name__)


class MusicGenerationError(Exception):
    """ElevenLabs music generation failed."""


def create_lyricist_agent(model: str | None = None):
    """Build the Lyricist chain and its output parser.

    The model defaults to OPENAI_MODEL (or gpt-5-mini). The reasoning and
    output_version settings assume a gpt-5-family reasoning model.
    """
    model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    parser = PydanticOutputParser(pydantic_object=LyricistOutput)
    prompt = ChatPromptTemplate.from_template(LYRICIST_PROMPT_TEMPLATE)
    # No `temperature`: gpt-5 reasoning models ignore it and langchain-openai
    # silently strips it from the request, so setting it only misleads.
    # `response_format` does carry through — it becomes `text.format` on the
    # Responses API, which is what keeps the output parseable JSON.
    llm = ChatOpenAI(
        model=model,
        reasoning={"effort": "low"},
        output_version="responses/v1",
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    chain = prompt | llm | parser
    return chain, parser


def validate_lyricist_output(output: LyricistOutput, expected_bars: int) -> None:
    """Coerce the Lyricist output to the expected bar count.

    Truncates extra bars and pads a small shortfall; raises if too few to pad.
    """
    actual_bars = len(output.bars)

    if actual_bars > expected_bars:
        logger.warning("Got %d bars, truncating to %d", actual_bars, expected_bars)
        output.bars = output.bars[:expected_bars]
    elif actual_bars < expected_bars:
        diff = expected_bars - actual_bars
        if diff <= 2:
            logger.warning("Got %d bars, padding %d to reach %d", actual_bars, diff, expected_bars)
            output.bars.extend(["yeah..."] * diff)
        else:
            raise ValueError(
                f"Expected {expected_bars} bars, got {actual_bars} (too few to pad)"
            )

    # Report the final bar count, not the pre-coercion one.
    final_bars = len(output.bars)
    total_words = sum(len(bar.split()) for bar in output.bars)
    logger.info("Validation passed: %d bars, %d total words", final_bars, total_words)


def generate_music(
    tts_prompt: str,
    seconds: float,
    api_key: str,
    output_path: str | Path,
) -> str:
    """Generate music via the ElevenLabs API and return the saved MP3 path.

    Args:
        output_path: Where to write the MP3. Each caller passes its own
            destination so concurrent battles can never collide.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    # Round up to a whole second to match the rounded TTS prompt and avoid
    # fractional durations the model may handle awkwardly.
    payload = {"prompt": tts_prompt, "music_length_ms": math.ceil(seconds) * 1000}

    logger.info(
        "Calling ElevenLabs API (duration: %ss, %sms)",
        seconds,
        payload["music_length_ms"],
    )

    try:
        response = requests.post(ELEVENLABS_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        logger.info("Music generated: %s", output_path)
        return str(output_path)
    except requests.exceptions.RequestException as e:
        error_msg = f"ElevenLabs API error: {e}"
        if e.response is not None:
            error_msg += f"\nResponse: {e.response.text}"
        raise MusicGenerationError(error_msg) from e
