#!/usr/bin/env python3
"""
Multiple test runs comparing LLM vs Python Grid Builder.

Tests with different opponent bars to verify consistency across various inputs.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, str(Path(__file__).parent))

from main import create_lyricist_agent, create_grid_builder_agent, validate_lyricist_output
from grid_builder_python import build_grid_from_lyrics
from prompts import TURN_INSTRUCTIONS


# Different test cases with various opponent bars
TEST_CASES = [
    {
        "name": "Original (from .env)",
        "opponent_bars": os.environ.get("OPPONENT_BARS", "").strip()
    },
    {
        "name": "Aggressive opening",
        "opponent_bars": "Step to me? You got no chance. I'm the king of this rap dance. Your rhymes are weak, mine advance. Watch me put you in a trance."
    },
    {
        "name": "Technical flow",
        "opponent_bars": "Syllables stacking mathematical precision. I'm division breaking down your weak composition. Listen to the rhythm it's a logical decision. Your mission? Submission to my lyrical vision."
    },
    {
        "name": "Short and punchy",
        "opponent_bars": "You talk big game but walk small. I stand tall, you gonna fall. That's all."
    },
    {
        "name": "Complex multi-rhyme",
        "opponent_bars": "Intricate patterns I weave through each bar. Raising the standard I'm setting it far. You reaching for stars but you stuck where you are. Meanwhile I'm traveling galaxies bizarre."
    }
]


def run_single_test(test_name: str, opponent_bars: str, bpm: int, seconds: float, model: str):
    """Run a single comparison test."""

    import math
    grid_beats = math.floor(bpm * seconds / 60.0)

    results = {
        "test_name": test_name,
        "opponent_bars": opponent_bars,
        "config": {"bpm": bpm, "seconds": seconds, "grid_beats": grid_beats},
        "success": False,
        "outputs_match": False,
        "timing": {},
        "verification": {}
    }

    try:
        # Step 1: Lyricist (shared)
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

        results["timing"]["lyricist"] = round(lyricist_duration, 2)
        results["lyricist_beats"] = lyricist_output.beats

        # Step 2a: LLM Grid Builder
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

        results["timing"]["llm_grid_builder"] = round(llm_duration, 2)
        results["timing"]["llm_total"] = round(lyricist_duration + llm_duration, 2)

        # Step 2b: Python Grid Builder
        python_start = time.time()
        python_grid_output = build_grid_from_lyrics(lyricist_output, bpm, seconds)
        python_duration = time.time() - python_start

        results["timing"]["python_grid_builder"] = round(python_duration, 6)
        results["timing"]["python_total"] = round(lyricist_duration + python_duration, 2)

        # Calculate savings
        time_saved = llm_duration - python_duration
        speedup = llm_duration / python_duration if python_duration > 0 else float('inf')
        total_speedup = (lyricist_duration + llm_duration) / (lyricist_duration + python_duration)

        results["timing"]["time_saved"] = round(time_saved, 2)
        results["timing"]["grid_builder_speedup"] = round(speedup, 0)
        results["timing"]["total_speedup"] = round(total_speedup, 2)

        # Verify outputs match
        plain_take_match = llm_grid_output.plain_take == python_grid_output.plain_take
        ms_per_beat_match = abs(llm_grid_output.ms_per_beat - python_grid_output.ms_per_beat) < 0.01
        grid_length_match = len(llm_grid_output.performance_grid) == len(python_grid_output.performance_grid)

        # Check grid details
        grids_match = True
        grid_mismatches = []
        for i, (llm_beat, py_beat) in enumerate(zip(llm_grid_output.performance_grid, python_grid_output.performance_grid)):
            if (llm_beat.beat != py_beat.beat or
                llm_beat.bar != py_beat.bar or
                llm_beat.beat_in_bar != py_beat.beat_in_bar or
                llm_beat.text != py_beat.text):
                grids_match = False
                grid_mismatches.append({
                    "beat_num": i + 1,
                    "llm": llm_beat.model_dump(),
                    "python": py_beat.model_dump()
                })

        results["verification"] = {
            "plain_take_match": plain_take_match,
            "ms_per_beat_match": ms_per_beat_match,
            "grid_length_match": grid_length_match,
            "grids_match": grids_match,
            "grid_mismatches": grid_mismatches
        }

        results["outputs_match"] = (plain_take_match and ms_per_beat_match and
                                    grid_length_match and grids_match)
        results["success"] = True

        results["llm_plain_take"] = llm_grid_output.plain_take
        results["python_plain_take"] = python_grid_output.plain_take

    except Exception as e:
        results["error"] = str(e)
        import traceback
        results["traceback"] = traceback.format_exc()

    return results


def main():
    """Run multiple tests and generate comprehensive report."""

    print("=" * 70)
    print("PYTHON GRID BUILDER - MULTIPLE TEST RUNS")
    print("=" * 70)

    bpm = int(os.environ.get("BPM", 90))
    seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 10))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    print(f"\n📊 Configuration: BPM={bpm}, Seconds={seconds}, Model={model}")
    print(f"\n🧪 Running {len(TEST_CASES)} test cases...\n")

    all_results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'=' * 70}")
        print(f"Opponent: {test_case['opponent_bars'][:80]}...")

        result = run_single_test(
            test_case['name'],
            test_case['opponent_bars'],
            bpm,
            seconds,
            model
        )

        if result["success"]:
            print(f"\n✓ Test completed successfully")
            print(f"  Lyricist: {result['timing']['lyricist']}s")
            print(f"  LLM Grid Builder: {result['timing']['llm_grid_builder']}s")
            print(f"  Python Grid Builder: {result['timing']['python_grid_builder']}s")
            print(f"  Time saved: {result['timing']['time_saved']}s")
            print(f"  Total speedup: {result['timing']['total_speedup']}x")
            print(f"  Outputs match: {result['outputs_match']}")

            if not result['outputs_match']:
                print(f"  ⚠️  WARNING: Outputs differ!")
                print(f"     {result['verification']}")
        else:
            print(f"❌ Test failed: {result.get('error', 'Unknown error')}")

        all_results.append(result)

        # Brief pause between tests
        if i < len(TEST_CASES):
            print("\nWaiting 2 seconds before next test...")
            time.sleep(2)

    # Generate summary
    print("\n\n" + "=" * 70)
    print("SUMMARY OF ALL TESTS")
    print("=" * 70)

    successful_tests = [r for r in all_results if r["success"]]
    matching_outputs = [r for r in successful_tests if r["outputs_match"]]

    print(f"\nTests run: {len(all_results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Outputs match: {len(matching_outputs)}")
    print(f"Match rate: {len(matching_outputs)/len(successful_tests)*100:.1f}%")

    if successful_tests:
        avg_lyricist = sum(r["timing"]["lyricist"] for r in successful_tests) / len(successful_tests)
        avg_llm_grid = sum(r["timing"]["llm_grid_builder"] for r in successful_tests) / len(successful_tests)
        avg_python_grid = sum(r["timing"]["python_grid_builder"] for r in successful_tests) / len(successful_tests)
        avg_time_saved = sum(r["timing"]["time_saved"] for r in successful_tests) / len(successful_tests)
        avg_speedup = sum(r["timing"]["total_speedup"] for r in successful_tests) / len(successful_tests)

        print(f"\n📊 Average Timings:")
        print(f"  Lyricist: {avg_lyricist:.2f}s")
        print(f"  LLM Grid Builder: {avg_llm_grid:.2f}s")
        print(f"  Python Grid Builder: {avg_python_grid:.6f}s")
        print(f"  Time saved per request: {avg_time_saved:.2f}s")
        print(f"  Average total speedup: {avg_speedup:.2f}x")

        print(f"\n💰 Cost Savings (estimated):")
        print(f"  Fewer API calls: 1 instead of 2 per turn")
        print(f"  Time reduction: ~{avg_llm_grid:.0f}s per turn")
        print(f"  In a 4-turn battle: ~{avg_llm_grid * 4:.0f}s total savings")

    # Save results
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"python_grid_multi_test_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {"bpm": bpm, "seconds": seconds, "model": model},
            "summary": {
                "tests_run": len(all_results),
                "successful": len(successful_tests),
                "outputs_match": len(matching_outputs),
                "match_rate": len(matching_outputs)/len(successful_tests)*100 if successful_tests else 0,
                "avg_time_saved": avg_time_saved if successful_tests else 0,
                "avg_speedup": avg_speedup if successful_tests else 0
            },
            "test_results": all_results
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n✓ All tests complete!")


if __name__ == "__main__":
    main()
