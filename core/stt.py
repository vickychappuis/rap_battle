"""Speech-to-text via the OpenAI transcription API."""

import logging
import os
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)


def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """Transcribe an audio file to text.

    Args:
        audio_path: Path to an audio file (mp3, wav, m4a, webm, ...).
        language: Language code for transcription (default "en").

    Raises:
        FileNotFoundError: If the audio file doesn't exist.
        ValueError: If OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    client = OpenAI(api_key=api_key)
    stt_model = os.environ.get("OPENAI_STT_MODEL", "whisper-1")

    logger.info("Transcribing %s...", path.name)
    with open(path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=stt_model,
            file=audio_file,
            language=language,
            prompt="rap battle freestyle hip-hop bars rhymes",
        )

    return transcription.text
