#!/usr/bin/env python3
"""
Test script to compare single-agent vs two-agent approach.

Single agent does both lyricist + grid builder work in one call.

Usage:
    python test_single_agent_timing.py
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

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from main import GridBuilderOutput
from prompts.unified_prompt import UNIFIED_LYRICIST_GRID_BUILDER_PROMPT_TEMPLATE
from prompts import TURN_INSTRUCTIONS, build_battle_context, TurnData


def create_unified_agent(model_name: str = "gpt-4o-mini"):
    """Create the unified lyricist+grid builder agent"""
    parser = PydanticOutputParser(pydantic_object=GridBuilderOutput)

    prompt = ChatPromptTemplate.from_template(UNIFIED_LYRICIST_GRID_BUILDER_PROMPT_TEMPLATE)

    llm = ChatOpenAI(
        model="gpt-5-mini",
        reasoning={"effort": "low"},
        output_version="responses/v1",
        temperature=0.7,  # Creative for lyric generation
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    chain = prompt | llm | parser

    return chain, parser


def test_single_agent_timing():
    """Test the single-agent approach and measure timing."""

    print("=" * 70)
    print("SINGLE-AGENT TIMING TEST")
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

    # Create unified agent
    print("🔧 Creating unified agent...")
    unified_chain, unified_parser = create_unified_agent(model)
    print("✓ Agent created\n")

    # ========================================================================
    # SINGLE UNIFIED AGENT
    # ========================================================================
    print("-" * 70)
    print("UNIFIED AGENT (Lyricist + Grid Builder)")
    print("-" * 70)

    unified_input = {
        "opponent_bars": opponent_bars,
        "bpm": bpm,
        "bars": 4,  # Default to 4 bars
        "seconds": seconds,
        "grid_beats": grid_beats,
        "grid_beats_minus_1": grid_beats - 1,
        "turn_number": 1,
        "total_turns": 4,
        "battle_context": "This is the opening exchange.",
        "turn_instructions": TURN_INSTRUCTIONS.get(1, "Deliver your best bars."),
        "format_instructions": unified_parser.get_format_instructions()
    }

    print("⏱️  Starting unified agent...")
    unified_start = time.time()

    try:
        unified_output = unified_chain.invoke(unified_input)
        unified_end = time.time()
        unified_duration = unified_end - unified_start

        print(f"✓ Unified agent completed in {unified_duration:.2f}s")
        print(f"\n🎵 Unified Agent Output:")
        print(f"   ms_per_beat: {unified_output.ms_per_beat:.2f}")
        print(f"   Performance grid length: {len(unified_output.performance_grid)}")
        print(f"   Plain take: {unified_output.plain_take[:100]}...")
        print(f"   TTS prompt length: {len(unified_output.tts_prompt)} chars")

        # Validate output
        if len(unified_output.performance_grid) != grid_beats:
            print(f"⚠️  Warning: Expected {grid_beats} beats, got {len(unified_output.performance_grid)}")

    except Exception as e:
        print(f"❌ Unified agent failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # LOAD COMPARISON DATA
    # ========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON WITH TWO-AGENT APPROACH")
    print("=" * 70)

    # Try to load the most recent two-agent timing
    test_results_dir = Path("test_results")
    if test_results_dir.exists():
        result_files = sorted(test_results_dir.glob("timing_*.json"))
        if result_files:
            latest_result = result_files[-1]
            with open(latest_result) as f:
                two_agent_data = json.load(f)

            two_agent_total = two_agent_data["timings"]["total_seconds"]
            lyricist_time = two_agent_data["timings"]["lyricist_seconds"]
            grid_builder_time = two_agent_data["timings"]["grid_builder_seconds"]

            print(f"\nTwo-Agent Approach (from {latest_result.name}):")
            print(f"  Lyricist:      {lyricist_time:>6.2f}s")
            print(f"  Grid Builder:  {grid_builder_time:>6.2f}s")
            print(f"  Total:         {two_agent_total:>6.2f}s")

            print(f"\nSingle-Agent Approach:")
            print(f"  Unified:       {unified_duration:>6.2f}s")

            speedup = two_agent_total / unified_duration
            time_saved = two_agent_total - unified_duration

            print(f"\n{'─' * 70}")
            print(f"Time saved:    {time_saved:>6.2f}s  ({abs(time_saved)/two_agent_total*100:>5.1f}%)")
            print(f"Speedup:       {speedup:>6.2f}x")
            print("=" * 70)
        else:
            print("\nNo two-agent results found. Run test_timing.py first.")
    else:
        print("\nNo test_results directory found. Run test_timing.py first.")

    # Save single-agent results
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "approach": "single-agent",
        "config": {
            "model": model,
            "bpm": bpm,
            "seconds": seconds,
            "grid_beats": grid_beats
        },
        "timings": {
            "unified_seconds": round(unified_duration, 2)
        },
        "output": {
            "ms_per_beat": unified_output.ms_per_beat,
            "grid_length": len(unified_output.performance_grid)
        }
    }

    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    results_file = output_dir / f"single_agent_{time.strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    test_single_agent_timing()
