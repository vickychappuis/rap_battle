"""
Pure Python Grid Builder - replaces LLM-based Grid Builder agent.

This module provides deterministic, instant grid building from lyricist output.
Since all grid building tasks are purely mathematical and template-based,
there's no need for an LLM - Python can do this in milliseconds.
"""

from models import GridBuilderOutput, PerformanceBeat, LyricistOutput


def build_grid_from_lyrics(lyricist_output: LyricistOutput, bpm: int, seconds: float) -> GridBuilderOutput:
    """
    Build performance grid and TTS prompt from lyricist output using pure Python.

    This replaces the Grid Builder LLM agent with deterministic logic.
    Executes in <1ms vs 12-15 seconds for LLM.

    Args:
        lyricist_output: Output from the Lyricist agent
        bpm: Beats per minute
        seconds: Total duration in seconds

    Returns:
        GridBuilderOutput with performance grid and TTS prompt
    """
    beats = lyricist_output.beats

    # 1. Calculate timing
    ms_per_beat = 60000.0 / bpm

    # 2. Build performance grid
    performance_grid = []
    for i, beat_text in enumerate(beats):
        beat_num = i + 1
        bar_num = (i // 4) + 1
        beat_in_bar = (i % 4) + 1

        performance_grid.append(
            PerformanceBeat(
                beat=beat_num,
                bar=bar_num,
                beat_in_bar=beat_in_bar,
                text=beat_text
            )
        )

    # 3. Create plain_take (strip pause beats so ElevenLabs only gets real words)
    plain_take = " ".join(b for b in beats if b != "...")

    # 4. Create TTS prompt
    # Round seconds up to the next whole number to avoid ugly repeating decimals
    # and give the model slight breathing room at the end
    import math
    rounded_seconds = math.ceil(seconds)

    tts_prompt = f"""Original male rap acapella ONLY. {bpm} BPM, 4/4. Length: {rounded_seconds}s, deliver as one clean take. Keep tight rhythm on the beat.

Lyrics:
{plain_take}"""

    return GridBuilderOutput(
        ms_per_beat=ms_per_beat,
        performance_grid=performance_grid,
        plain_take=plain_take,
        tts_prompt=tts_prompt
    )
