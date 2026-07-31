"""
Bar-based TTS prompt builder.

Assembles lyricist bars into a TTS prompt for ElevenLabs music generation.
"""

import math

from core.models import GridBuilderOutput, LyricistOutput


def build_grid_from_lyrics(lyricist_output: LyricistOutput, bpm: int, seconds: float) -> GridBuilderOutput:
    """
    Build TTS prompt from lyricist bars.

    Args:
        lyricist_output: Output from the Lyricist agent (bars + mood_arc)
        bpm: Beats per minute
        seconds: Total duration in seconds

    Returns:
        GridBuilderOutput with plain_take and TTS prompt
    """
    ms_per_beat = 60000.0 / bpm
    rounded_seconds = math.ceil(seconds)

    # Join bars with newlines for the lyrics block
    plain_take = "\n".join(lyricist_output.bars)

    # Build mood description for the TTS prompt
    mood = lyricist_output.mood_arc or "confident and aggressive"

    tts_prompt = f"""Rap acapella ONLY, no instruments. {bpm} BPM, 4/4 time. Length: {rounded_seconds}s. One clean take.
Delivery: {mood}. Start laid-back, build energy, finish explosive and hard-hitting.

Lyrics:
{plain_take}"""

    return GridBuilderOutput(
        ms_per_beat=ms_per_beat,
        plain_take=plain_take,
        tts_prompt=tts_prompt
    )
