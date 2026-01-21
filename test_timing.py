#!/usr/bin/env python3
"""
Test script to measure timing of each agent in the pipeline.

Usage:
    python test_timing.py
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    create_lyricist_agent,
    create_grid_builder_agent,
    validate_lyricist_output,
)


def test_pipeline_timing():
    """Test the full pipeline and measure timing for each agent."""

    print("=" * 70)
    print("AGENT TIMING TEST")
    print("=" * 70)

    # Load configuration from environment
    opponent_bars = os.environ.get("OPPONENT_BARS", "").strip()
    if not opponent_bars:
        print("❌ Error: OPPONENT_BARS not set in .env file")
        return

    bpm = int(os.environ.get("BPM", 90))
    seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 10))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Calculate timing
    import math
    total_beats_exact = bpm * seconds / 60.0
    grid_beats = math.floor(total_beats_exact)

    print(f"\n📊 Configuration:")
    print(f"   Model: {model}")
    print(f"   BPM: {bpm}")
    print(f"   Seconds: {seconds}")
    print(f"   Grid beats: {grid_beats}")
    print(f"\n🎤 Opponent bars:")
    print(f"   {opponent_bars[:100]}..." if len(opponent_bars) > 100 else f"   {opponent_bars}")
    print()

    # Create agents
    print("🔧 Creating agents...")
    lyricist_chain, lyricist_parser = create_lyricist_agent(model)
    grid_builder_chain, grid_builder_parser = create_grid_builder_agent(model)
    print("✓ Agents created\n")

    # ========================================================================
    # AGENT 1: LYRICIST
    # ========================================================================
    print("-" * 70)
    print("AGENT 1: LYRICIST")
    print("-" * 70)

    lyricist_input = {
        "opponent_bars": opponent_bars,
        "bpm": bpm,
        "bars": 4,  # Default to 4 bars
        "seconds": seconds,
        "grid_beats": grid_beats,
        "grid_beats_minus_1": grid_beats - 1,
        "turn_number": 1,
        "total_turns": 4,
        "battle_context": "This is the opening exchange.",
        "turn_instructions": "This is your opening response. Establish your style, counter their intro, and set the tone for the battle.",
        "format_instructions": lyricist_parser.get_format_instructions()
    }

    print("⏱️  Starting Lyricist agent...")
    lyricist_start = time.time()

    try:
        lyricist_output = lyricist_chain.invoke(lyricist_input)
        lyricist_end = time.time()
        lyricist_duration = lyricist_end - lyricist_start

        print(f"✓ Lyricist completed in {lyricist_duration:.2f}s")
        print(f"\n📝 Lyricist Output:")
        print(f"   Grid beats: {lyricist_output.grid_beats}")
        print(f"   Number of beats: {len(lyricist_output.beats)}")
        print(f"   Sample beats: {lyricist_output.beats[:3]}...")

        # Validate
        print(f"\n🔍 Validating Lyricist output...")
        validate_lyricist_output(lyricist_output, grid_beats)
        print(f"✓ Validation passed")

    except Exception as e:
        print(f"❌ Lyricist failed: {e}")
        return

    # ========================================================================
    # AGENT 2: GRID BUILDER
    # ========================================================================
    print("\n" + "-" * 70)
    print("AGENT 2: GRID BUILDER")
    print("-" * 70)

    grid_builder_input = {
        "lyricist_json": json.dumps(lyricist_output.model_dump(), indent=2),
        "bpm": bpm,
        "seconds": seconds,
        "format_instructions": grid_builder_parser.get_format_instructions()
    }

    print("⏱️  Starting Grid Builder agent...")
    grid_builder_start = time.time()

    try:
        grid_builder_output = grid_builder_chain.invoke(grid_builder_input)
        grid_builder_end = time.time()
        grid_builder_duration = grid_builder_end - grid_builder_start

        print(f"✓ Grid Builder completed in {grid_builder_duration:.2f}s")
        print(f"\n🎵 Grid Builder Output:")
        print(f"   ms_per_beat: {grid_builder_output.ms_per_beat:.2f}")
        print(f"   Performance grid length: {len(grid_builder_output.performance_grid)}")
        print(f"   Plain take: {grid_builder_output.plain_take[:100]}...")
        print(f"   TTS prompt length: {len(grid_builder_output.tts_prompt)} chars")

    except Exception as e:
        print(f"❌ Grid Builder failed: {e}")
        return

    # ========================================================================
    # SUMMARY
    # ========================================================================
    total_duration = grid_builder_end - lyricist_start

    print("\n" + "=" * 70)
    print("TIMING SUMMARY")
    print("=" * 70)
    print(f"Lyricist:      {lyricist_duration:>8.2f}s  ({lyricist_duration/total_duration*100:>5.1f}%)")
    print(f"Grid Builder:  {grid_builder_duration:>8.2f}s  ({grid_builder_duration/total_duration*100:>5.1f}%)")
    print(f"{'─' * 70}")
    print(f"Total:         {total_duration:>8.2f}s  (100.0%)")
    print("=" * 70)

    # Save detailed results to JSON
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "model": model,
            "bpm": bpm,
            "seconds": seconds,
            "grid_beats": grid_beats
        },
        "timings": {
            "lyricist_seconds": round(lyricist_duration, 2),
            "grid_builder_seconds": round(grid_builder_duration, 2),
            "total_seconds": round(total_duration, 2)
        },
        "lyricist_output": {
            "grid_beats": lyricist_output.grid_beats,
            "num_beats": len(lyricist_output.beats)
        },
        "grid_builder_output": {
            "ms_per_beat": grid_builder_output.ms_per_beat,
            "grid_length": len(grid_builder_output.performance_grid)
        }
    }

    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    results_file = output_dir / f"timing_{time.strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    test_pipeline_timing()
