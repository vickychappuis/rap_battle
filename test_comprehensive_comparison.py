#!/usr/bin/env python3
"""
Comprehensive comparison test between two-agent and single-agent approaches.

This test:
1. Runs both approaches
2. Validates output structure and quality
3. Compares timing, outputs, and quality metrics
4. Saves detailed results to a single file for review

Usage:
    python test_comprehensive_comparison.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
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
from test_single_agent_timing import create_unified_agent
from prompts import TURN_INSTRUCTIONS


def validate_grid_builder_output(output, grid_beats: int) -> dict:
    """Validate Grid Builder output and return quality metrics."""
    issues = []
    warnings = []

    # Check performance grid length
    if len(output.performance_grid) != grid_beats:
        issues.append(f"Expected {grid_beats} beats in grid, got {len(output.performance_grid)}")

    # Check ms_per_beat calculation
    expected_ms_per_beat = 60000 / 90  # BPM is 90
    if abs(output.ms_per_beat - expected_ms_per_beat) > 1:
        warnings.append(f"ms_per_beat seems off: {output.ms_per_beat:.2f} vs expected {expected_ms_per_beat:.2f}")

    # Check beat numbering
    for i, beat_item in enumerate(output.performance_grid):
        expected_beat = i + 1
        if beat_item.beat != expected_beat:
            issues.append(f"Beat {i+1} has wrong beat number: {beat_item.beat}")

        # Check bar calculation
        expected_bar = ((i) // 4) + 1
        if beat_item.bar != expected_bar:
            warnings.append(f"Beat {i+1} has wrong bar: {beat_item.bar} vs expected {expected_bar}")

        # Check beat_in_bar
        expected_beat_in_bar = (i % 4) + 1
        if beat_item.beat_in_bar != expected_beat_in_bar:
            warnings.append(f"Beat {i+1} has wrong beat_in_bar: {beat_item.beat_in_bar} vs expected {expected_beat_in_bar}")

    # Check plain_take is not empty
    if not output.plain_take or not output.plain_take.strip():
        issues.append("plain_take is empty")

    # Check tts_prompt is not empty
    if not output.tts_prompt or not output.tts_prompt.strip():
        issues.append("tts_prompt is empty")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


def run_two_agent_approach(opponent_bars: str, bpm: int, seconds: float, grid_beats: int, model: str):
    """Run the two-agent approach and return results."""
    print("=" * 70)
    print("TWO-AGENT APPROACH")
    print("=" * 70)

    results = {
        "approach": "two-agent",
        "success": False,
        "timing": {},
        "validation": {},
        "outputs": {}
    }

    try:
        # Create agents
        print("🔧 Creating agents...")
        lyricist_chain, lyricist_parser = create_lyricist_agent(model)
        grid_builder_chain, grid_builder_parser = create_grid_builder_agent(model)
        print("✓ Agents created\n")

        # Step 1: Lyricist
        print("📝 Running Lyricist...")
        lyricist_start = time.time()

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

        lyricist_output = lyricist_chain.invoke(lyricist_input)
        lyricist_duration = time.time() - lyricist_start
        print(f"✓ Lyricist completed in {lyricist_duration:.2f}s")

        # Validate lyricist output
        print("🔍 Validating Lyricist output...")
        try:
            validate_lyricist_output(lyricist_output, grid_beats)
            results["validation"]["lyricist"] = {
                "valid": True,
                "issues": []
            }
            print("✓ Lyricist validation passed")
        except Exception as e:
            results["validation"]["lyricist"] = {
                "valid": False,
                "issues": [str(e)]
            }
            print(f"❌ Lyricist validation failed: {e}")
            return results

        # Step 2: Grid Builder
        print("\n🎵 Running Grid Builder...")
        grid_builder_start = time.time()

        grid_builder_input = {
            "lyricist_json": json.dumps(lyricist_output.model_dump(), indent=2),
            "bpm": bpm,
            "seconds": seconds,
            "format_instructions": grid_builder_parser.get_format_instructions()
        }

        grid_builder_output = grid_builder_chain.invoke(grid_builder_input)
        grid_builder_duration = time.time() - grid_builder_start
        print(f"✓ Grid Builder completed in {grid_builder_duration:.2f}s")

        # Validate grid builder output
        print("🔍 Validating Grid Builder output...")
        validation_result = validate_grid_builder_output(grid_builder_output, grid_beats)
        results["validation"]["grid_builder"] = validation_result

        if validation_result["valid"]:
            print("✓ Grid Builder validation passed")
        else:
            print(f"❌ Grid Builder validation failed: {validation_result['issues']}")

        if validation_result["warnings"]:
            print(f"⚠️  Grid Builder warnings: {validation_result['warnings']}")

        # Store results
        results["success"] = validation_result["valid"]
        results["timing"] = {
            "lyricist_seconds": round(lyricist_duration, 2),
            "grid_builder_seconds": round(grid_builder_duration, 2),
            "total_seconds": round(lyricist_duration + grid_builder_duration, 2)
        }
        results["outputs"] = {
            "lyricist": {
                "grid_beats": lyricist_output.grid_beats,
                "beats": lyricist_output.beats
            },
            "grid_builder": {
                "ms_per_beat": grid_builder_output.ms_per_beat,
                "performance_grid": [beat.model_dump() for beat in grid_builder_output.performance_grid],
                "plain_take": grid_builder_output.plain_take,
                "tts_prompt": grid_builder_output.tts_prompt
            }
        }

    except Exception as e:
        print(f"❌ Two-agent approach failed: {e}")
        results["error"] = str(e)
        import traceback
        results["traceback"] = traceback.format_exc()

    return results


def run_single_agent_approach(opponent_bars: str, bpm: int, seconds: float, grid_beats: int, model: str):
    """Run the single-agent approach and return results."""
    print("\n" + "=" * 70)
    print("SINGLE-AGENT APPROACH")
    print("=" * 70)

    results = {
        "approach": "single-agent",
        "success": False,
        "timing": {},
        "validation": {},
        "outputs": {}
    }

    try:
        # Create agent
        print("🔧 Creating unified agent...")
        unified_chain, unified_parser = create_unified_agent(model)
        print("✓ Agent created\n")

        # Run unified agent
        print("⚡ Running unified agent...")
        unified_start = time.time()

        unified_input = {
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
            "format_instructions": unified_parser.get_format_instructions()
        }

        unified_output = unified_chain.invoke(unified_input)
        unified_duration = time.time() - unified_start
        print(f"✓ Unified agent completed in {unified_duration:.2f}s")

        # Validate output (same as grid builder validation)
        print("🔍 Validating unified output...")
        validation_result = validate_grid_builder_output(unified_output, grid_beats)
        results["validation"]["unified"] = validation_result

        if validation_result["valid"]:
            print("✓ Unified validation passed")
        else:
            print(f"❌ Unified validation failed: {validation_result['issues']}")

        if validation_result["warnings"]:
            print(f"⚠️  Unified warnings: {validation_result['warnings']}")

        # Store results
        results["success"] = validation_result["valid"]
        results["timing"] = {
            "unified_seconds": round(unified_duration, 2)
        }
        results["outputs"] = {
            "unified": {
                "ms_per_beat": unified_output.ms_per_beat,
                "performance_grid": [beat.model_dump() for beat in unified_output.performance_grid],
                "plain_take": unified_output.plain_take,
                "tts_prompt": unified_output.tts_prompt
            }
        }

    except Exception as e:
        print(f"❌ Single-agent approach failed: {e}")
        results["error"] = str(e)
        import traceback
        results["traceback"] = traceback.format_exc()

    return results


def main():
    """Run comprehensive comparison."""
    print("=" * 70)
    print("COMPREHENSIVE COMPARISON TEST")
    print("=" * 70)

    # Load configuration
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
    print(f"   {opponent_bars}\n")

    # Run both approaches
    two_agent_results = run_two_agent_approach(opponent_bars, bpm, seconds, grid_beats, model)
    single_agent_results = run_single_agent_approach(opponent_bars, bpm, seconds, grid_beats, model)

    # Create comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    comparison = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "model": model,
            "bpm": bpm,
            "seconds": seconds,
            "grid_beats": grid_beats,
            "opponent_bars": opponent_bars
        },
        "two_agent": two_agent_results,
        "single_agent": single_agent_results
    }

    # Print summary
    if two_agent_results["success"]:
        print(f"\n✓ Two-Agent: {two_agent_results['timing']['total_seconds']}s")
    else:
        print(f"\n❌ Two-Agent: FAILED")

    if single_agent_results["success"]:
        print(f"✓ Single-Agent: {single_agent_results['timing']['unified_seconds']}s")
    else:
        print(f"❌ Single-Agent: FAILED")

    if two_agent_results["success"] and single_agent_results["success"]:
        speedup = two_agent_results["timing"]["total_seconds"] / single_agent_results["timing"]["unified_seconds"]
        time_saved = two_agent_results["timing"]["total_seconds"] - single_agent_results["timing"]["unified_seconds"]
        print(f"\n⚡ Speedup: {speedup:.2f}x ({time_saved:.2f}s saved)")

    # Save to file
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"comparison_{time.strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\n💾 Detailed comparison saved to: {output_file}")

    # Also save a human-readable version
    readme_file = output_dir / f"comparison_{time.strftime('%Y%m%d_%H%M%S')}_READABLE.txt"
    with open(readme_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("COMPREHENSIVE COMPARISON - READABLE FORMAT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Timestamp: {comparison['timestamp']}\n\n")

        f.write("CONFIGURATION:\n")
        f.write(f"  Model: {model}\n")
        f.write(f"  BPM: {bpm}\n")
        f.write(f"  Seconds: {seconds}\n")
        f.write(f"  Grid beats: {grid_beats}\n")
        f.write(f"  Opponent bars: {opponent_bars}\n\n")

        f.write("=" * 70 + "\n")
        f.write("TWO-AGENT APPROACH\n")
        f.write("=" * 70 + "\n\n")

        if two_agent_results["success"]:
            f.write(f"✓ SUCCESS\n\n")
            f.write(f"TIMING:\n")
            f.write(f"  Lyricist: {two_agent_results['timing']['lyricist_seconds']}s\n")
            f.write(f"  Grid Builder: {two_agent_results['timing']['grid_builder_seconds']}s\n")
            f.write(f"  Total: {two_agent_results['timing']['total_seconds']}s\n\n")

            f.write(f"VALIDATION:\n")
            f.write(f"  Lyricist: {'✓ PASS' if two_agent_results['validation']['lyricist']['valid'] else '❌ FAIL'}\n")
            f.write(f"  Grid Builder: {'✓ PASS' if two_agent_results['validation']['grid_builder']['valid'] else '❌ FAIL'}\n\n")

            f.write(f"LYRICIST OUTPUT (Beats):\n")
            for i, beat in enumerate(two_agent_results['outputs']['lyricist']['beats'], 1):
                f.write(f"  Beat {i}: \"{beat}\"\n")

            f.write(f"\nGRID BUILDER OUTPUT:\n")
            f.write(f"  Plain take: {two_agent_results['outputs']['grid_builder']['plain_take']}\n\n")
            f.write(f"  TTS Prompt:\n{two_agent_results['outputs']['grid_builder']['tts_prompt']}\n\n")
        else:
            f.write(f"❌ FAILED\n")
            f.write(f"Error: {two_agent_results.get('error', 'Unknown')}\n\n")

        f.write("=" * 70 + "\n")
        f.write("SINGLE-AGENT APPROACH\n")
        f.write("=" * 70 + "\n\n")

        if single_agent_results["success"]:
            f.write(f"✓ SUCCESS\n\n")
            f.write(f"TIMING:\n")
            f.write(f"  Unified: {single_agent_results['timing']['unified_seconds']}s\n\n")

            f.write(f"VALIDATION:\n")
            f.write(f"  Unified: {'✓ PASS' if single_agent_results['validation']['unified']['valid'] else '❌ FAIL'}\n\n")

            f.write(f"UNIFIED OUTPUT:\n")
            f.write(f"  Plain take: {single_agent_results['outputs']['unified']['plain_take']}\n\n")
            f.write(f"  TTS Prompt:\n{single_agent_results['outputs']['unified']['tts_prompt']}\n\n")

            f.write(f"PERFORMANCE GRID (Beat-by-beat):\n")
            for beat_item in single_agent_results['outputs']['unified']['performance_grid']:
                f.write(f"  Beat {beat_item['beat']} (Bar {beat_item['bar']}, beat {beat_item['beat_in_bar']}): \"{beat_item['text']}\"\n")
        else:
            f.write(f"❌ FAILED\n")
            f.write(f"Error: {single_agent_results.get('error', 'Unknown')}\n\n")

        if two_agent_results["success"] and single_agent_results["success"]:
            f.write("\n" + "=" * 70 + "\n")
            f.write("COMPARISON\n")
            f.write("=" * 70 + "\n\n")

            speedup = two_agent_results["timing"]["total_seconds"] / single_agent_results["timing"]["unified_seconds"]
            time_saved = two_agent_results["timing"]["total_seconds"] - single_agent_results["timing"]["unified_seconds"]

            f.write(f"Two-Agent Total: {two_agent_results['timing']['total_seconds']}s\n")
            f.write(f"Single-Agent Total: {single_agent_results['timing']['unified_seconds']}s\n")
            f.write(f"Time Saved: {time_saved:.2f}s\n")
            f.write(f"Speedup: {speedup:.2f}x\n\n")

            f.write("QUALITY COMPARISON:\n")
            f.write(f"  Two-Agent Plain Take:\n    {two_agent_results['outputs']['grid_builder']['plain_take']}\n\n")
            f.write(f"  Single-Agent Plain Take:\n    {single_agent_results['outputs']['unified']['plain_take']}\n\n")

    print(f"📄 Readable comparison saved to: {readme_file}")
    print("\n✓ Comparison complete!")


if __name__ == "__main__":
    main()
