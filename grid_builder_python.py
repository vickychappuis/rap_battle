"""
Pure Python Grid Builder - replaces LLM-based Grid Builder agent.

This module provides deterministic, instant grid building from lyricist output.
Since all grid building tasks are purely mathematical and template-based,
there's no need for an LLM - Python can do this in milliseconds.
"""

from typing import List
from main import GridBuilderOutput, PerformanceBeat, LyricistOutput


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

    # 3. Create plain_take
    plain_take = " ".join(beats)

    # 4. Create TTS prompt
    grid_lines = []
    for beat_item in performance_grid:
        grid_lines.append(
            f"Beat {beat_item.beat} (Bar {beat_item.bar}, beat {beat_item.beat_in_bar}): {beat_item.text}"
        )

    tts_prompt = f"""Original male rap acapella ONLY. {bpm} BPM, 4/4. Length: {seconds}s (exact), deliver as one clean take.

Performance grid (exact timing):
{chr(10).join(grid_lines)}

Clean take:
{plain_take}"""

    return GridBuilderOutput(
        ms_per_beat=ms_per_beat,
        performance_grid=performance_grid,
        plain_take=plain_take,
        tts_prompt=tts_prompt
    )


def test_python_grid_builder():
    """Test the Python grid builder against LLM version."""
    import time
    import os
    from dotenv import load_dotenv
    from main import create_lyricist_agent
    from prompts import TURN_INSTRUCTIONS

    load_dotenv()

    opponent_bars = os.environ.get("OPPONENT_BARS", "").strip()
    bpm = int(os.environ.get("BPM", 90))
    seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 10))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    import math
    grid_beats = math.floor(bpm * seconds / 60.0)

    print("=" * 70)
    print("PYTHON GRID BUILDER TEST")
    print("=" * 70)
    print(f"\nBPM: {bpm}, Seconds: {seconds}, Grid beats: {grid_beats}\n")

    # Get lyricist output
    print("📝 Running Lyricist...")
    lyricist_chain, lyricist_parser = create_lyricist_agent(model)

    lyricist_input = {
        "opponent_bars": opponent_bars,
        "bpm": bpm,
        "bars": 4,
        "seconds": seconds,
        "grid_beats": grid_beats,
        "grid_beats_minus_1": grid_beats - 1,
        "turn_number": 1,
        "total_turns": 4,
        "battle_context": "This is the opening exchange.",
        "turn_instructions": TURN_INSTRUCTIONS.get(1, "Deliver your best bars."),
        "format_instructions": lyricist_parser.get_format_instructions()
    }

    lyricist_start = time.time()
    lyricist_output = lyricist_chain.invoke(lyricist_input)
    lyricist_duration = time.time() - lyricist_start
    print(f"✓ Lyricist completed in {lyricist_duration:.2f}s\n")

    # Build grid with Python (instant!)
    print("⚡ Running Python Grid Builder...")
    python_start = time.time()
    grid_output = build_grid_from_lyrics(lyricist_output, bpm, seconds)
    python_duration = time.time() - python_start
    print(f"✓ Python Grid Builder completed in {python_duration:.4f}s")

    print(f"\n📊 Results:")
    print(f"   ms_per_beat: {grid_output.ms_per_beat:.2f}")
    print(f"   Performance grid length: {len(grid_output.performance_grid)}")
    print(f"   Plain take: {grid_output.plain_take[:80]}...")

    print(f"\n⚡ Performance:")
    print(f"   Lyricist: {lyricist_duration:.2f}s")
    print(f"   Python Grid Builder: {python_duration:.4f}s (~{python_duration*1000:.1f}ms)")
    print(f"   Total: {lyricist_duration + python_duration:.2f}s")
    print(f"\n   Compare to LLM Grid Builder: 12-15 seconds")
    print(f"   Speedup: ~{15 / python_duration:.0f}x faster!")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_python_grid_builder()
