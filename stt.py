"""
Speech-to-Text module using OpenAI Whisper API

Provides:
- Real-time audio recording from microphone
- Audio transcription via OpenAI Whisper
"""

import os
import tempfile
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from openai import OpenAI


def record_audio(
    duration: float,
    output_path: str | None = None,
    sample_rate: int = 44100
) -> str:
    """
    Record audio from the default microphone.

    Args:
        duration: Recording duration in seconds
        output_path: Path to save the audio file. If None, uses a temp file.
        sample_rate: Audio sample rate (default 44100 Hz)

    Returns:
        Path to the recorded audio file (WAV format)
    """
    if output_path is None:
        # Create temp file that won't be auto-deleted
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

    print(f"Recording for {duration} seconds...")
    print("Speak now!")

    # Record audio from microphone
    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()  # Wait until recording is finished

    print("Recording complete.")

    # Save to WAV file
    sf.write(output_path, audio_data, sample_rate)

    return output_path


def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """
    Transcribe audio file to text using OpenAI Whisper API.

    Args:
        audio_path: Path to audio file (mp3, wav, m4a, webm, etc.)
        language: Language code for transcription (default "en")

    Returns:
        Transcribed text

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If OPENAI_API_KEY is not set
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    client = OpenAI(api_key=api_key)

    print(f"Transcribing {audio_path.name}...")

    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            prompt="rap battle freestyle hip-hop bars rhymes",  # Context hint
        )

    return transcription.text


def record_and_transcribe(duration: float, language: str = "en") -> str:
    """
    Record audio from microphone and transcribe it.

    Convenience function that combines record_audio and transcribe_audio.

    Args:
        duration: Recording duration in seconds
        language: Language code for transcription (default "en")

    Returns:
        Transcribed text
    """
    audio_path = record_audio(duration)

    try:
        transcription = transcribe_audio(audio_path, language)
    finally:
        # Clean up temp file
        Path(audio_path).unlink(missing_ok=True)

    return transcription


if __name__ == "__main__":
    # Quick test
    from dotenv import load_dotenv
    load_dotenv()

    print("=== STT Module Test ===")
    duration = float(input("Enter recording duration (seconds): ") or "5")

    text = record_and_transcribe(duration)
    print(f"\nTranscription:\n{text}")
