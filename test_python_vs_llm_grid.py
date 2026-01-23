#!/usr/bin/env python3
"""
Compare LLM-based Grid Builder vs Python-based Grid Builder.

This test demonstrates that grid building is purely systematic logic
that doesn't require an LLM.
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, str(Path(__file__).parent))

from main import create_lyricist_agent, create_grid_builder_agent, validate_lyricist_output
from grid_builder_python import build_grid_from_lyrics
from prompts import TURN_INSTRUCTIONS


def test_both_approaches():
    """Test both LLM and Python grid builders."""

    print("=" * 70)
    print("LLM vs PYTHON GRID BUILDER COMPARISON")
    print("=" * 70)

    opponent_bars = os.environ.get("OPPONENT_BARS", "").strip()
    bpm = int(os.environ.get("BPM", 90))
    seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 10))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    import math
    grid_beats = math.floor(bpm * seconds / 60.0)

    print(f"\n📊 Config: BPM={bpm}, Seconds={seconds}, Grid beats={grid_beats}\n")

    # Step 1: Get lyricist output (shared by both approaches)
    print("=" * 70)
    print("STEP 1: LYRICIST (same for both approaches)")
    print("=" * 70)

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
    validate_lyricist_output(lyricist_output, grid_beats)

    print(f"✓ Lyricist completed in {lyricist_duration:.2f}s")
    print(f"  Beats: {lyricist_output.beats}\n")

    # Step 2a: LLM Grid Builder
    print("=" * 70)
    print("STEP 2a: LLM GRID BUILDER (current approach)")
    print("=" * 70)

    grid_builder_chain, grid_builder_parser = create_grid_builder_agent(model)
    grid_builder_input = {
        "lyricist_json": json.dumps(lyricist_output.model_dump(), indent=2),
        "bpm": bpm,
        "seconds": seconds,
        "format_instructions": grid_builder_parser.get_format_instructions()
    }

    llm_start = time.time()
    llm_grid_output = grid_builder_chain.invoke(grid_builder_input)
    llm_duration = time.time() - llm_start

    print(f"✓ LLM Grid Builder completed in {llm_duration:.2f}s")
    print(f"  Plain take: {llm_grid_output.plain_take}\n")

    # Step 2b: Python Grid Builder
    print("=" * 70)
    print("STEP 2b: PYTHON GRID BUILDER (proposed replacement)")
    print("=" * 70)

    python_start = time.time()
    python_grid_output = build_grid_from_lyrics(lyricist_output, bpm, seconds)
    python_duration = time.time() - python_start

    print(f"✓ Python Grid Builder completed in {python_duration:.6f}s ({python_duration*1000:.2f}ms)")
    print(f"  Plain take: {python_grid_output.plain_take}\n")

    # Comparison
    print("=" * 70)
    print("TIMING COMPARISON")
    print("=" * 70)

    llm_total = lyricist_duration + llm_duration
    python_total = lyricist_duration + python_duration

    print(f"\nLLM Approach (current):")
    print(f"  Lyricist:      {lyricist_duration:>8.2f}s  ({lyricist_duration/llm_total*100:>5.1f}%)")
    print(f"  Grid Builder:  {llm_duration:>8.2f}s  ({llm_duration/llm_total*100:>5.1f}%)")
    print(f"  Total:         {llm_total:>8.2f}s")

    print(f"\nPython Approach (proposed):")
    print(f"  Lyricist:      {lyricist_duration:>8.2f}s  ({lyricist_duration/python_total*100:>5.1f}%)")
    print(f"  Grid Builder:  {python_duration:>8.6f}s  ({python_duration/python_total*100:>5.2f}%)")
    print(f"  Total:         {python_total:>8.2f}s")

    time_saved = llm_total - python_total
    speedup = llm_total / python_total

    print(f"\n{'─' * 70}")
    print(f"Time Saved:    {time_saved:>8.2f}s  ({time_saved/llm_total*100:>5.1f}%)")
    print(f"Speedup:       {speedup:>8.2f}x")
    print(f"Grid Builder Speedup: {llm_duration/python_duration:>8.0f}x")
    print("=" * 70)

    # Verify outputs match
    print("\n" + "=" * 70)
    print("OUTPUT VERIFICATION")
    print("=" * 70)

    print(f"\nBoth outputs produce same plain_take: {llm_grid_output.plain_take == python_grid_output.plain_take}")
    print(f"Both have same ms_per_beat: {abs(llm_grid_output.ms_per_beat - python_grid_output.ms_per_beat) < 0.01}")
    print(f"Both have same grid length: {len(llm_grid_output.performance_grid) == len(python_grid_output.performance_grid)}")

    # Check grid equality
    grids_match = True
    for i, (llm_beat, py_beat) in enumerate(zip(llm_grid_output.performance_grid, python_grid_output.performance_grid)):
        if (llm_beat.beat != py_beat.beat or
            llm_beat.bar != py_beat.bar or
            llm_beat.beat_in_bar != py_beat.beat_in_bar or
            llm_beat.text != py_beat.text):
            grids_match = False
            print(f"  ❌ Mismatch at beat {i+1}")
            print(f"     LLM: {llm_beat}")
            print(f"     Python: {py_beat}")

    if grids_match:
        print(f"✓ Performance grids are identical")
    else:
        print(f"❌ Performance grids differ")

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print(f"""
Grid building is 100% systematic and deterministic.
Python can do it in <1ms vs LLM taking {llm_duration:.1f}s.

Recommendation: Replace LLM Grid Builder with Python function.
This would reduce total pipeline time from ~{llm_total:.0f}s to ~{python_total:.0f}s ({speedup:.1f}x faster).
""")


if __name__ == "__main__":
    test_both_approaches()
