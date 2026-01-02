#!/usr/bin/env python3
"""
Timing Comparison Script for OpenAI Models
Compares execution time between gpt-5-mini and gpt-5-nano
"""

import os
import time
import json
from dotenv import load_dotenv
from main import RapBattleOrchestrator

# Load environment variables
load_dotenv()


def run_pipeline_with_model(model_name: str) -> dict:
    """
    Run the rap battle pipeline with a specific model

    Args:
        model_name: The OpenAI model to use

    Returns:
        dict with 'duration' (seconds) and 'results'
    """
    print(f"\n{'='*60}")
    print(f"Testing with model: {model_name}")
    print(f"{'='*60}\n")

    # Temporarily set the model in environment
    original_model = os.environ.get("OPENAI_MODEL")
    os.environ["OPENAI_MODEL"] = model_name

    try:
        # Start timing
        start_time = time.time()

        # Run the pipeline
        orchestrator = RapBattleOrchestrator()
        results = orchestrator.run()

        # Calculate duration
        end_time = time.time()
        duration = end_time - start_time

        print(f"\n⏱️  Total execution time: {duration:.2f} seconds")

        return {
            "model": model_name,
            "duration": duration,
            "results": results
        }

    except Exception as e:
        print(f"❌ Error with {model_name}: {e}")
        raise

    finally:
        # Restore original model setting
        if original_model:
            os.environ["OPENAI_MODEL"] = original_model


def compare_models():
    """
    Compare execution time between gpt-5-mini and gpt-5-nano
    """
    print("\n" + "="*60)
    print("OpenAI Model Performance Comparison")
    print("="*60)

    # Verify required environment variables
    required_vars = ["OPENAI_API_KEY", "BPM", "SECONDS_LENGTH_OF_ANSWER", "OPPONENT_BARS"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        return

    # Run tests for both models
    models = ["gpt-5-mini", "gpt-5-nano"]
    results = {}

    for model in models:
        try:
            result = run_pipeline_with_model(model)
            results[model] = result
        except Exception as e:
            print(f"\n❌ Failed to test {model}: {e}")
            return

    # Display comparison
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON RESULTS")
    print("="*60)

    mini_time = results["gpt-5-mini"]["duration"]
    nano_time = results["gpt-5-nano"]["duration"]

    print(f"\n📊 Execution Times:")
    print(f"  gpt-5-mini: {mini_time:.2f} seconds")
    print(f"  gpt-5-nano: {nano_time:.2f} seconds")

    print(f"\n📈 Performance Difference:")
    time_diff = abs(mini_time - nano_time)
    faster_model = "gpt-5-mini" if mini_time < nano_time else "gpt-5-nano"
    slower_model = "gpt-5-nano" if faster_model == "gpt-5-mini" else "gpt-5-mini"

    if mini_time < nano_time:
        percentage = ((nano_time - mini_time) / nano_time) * 100
        print(f"  {faster_model} is {time_diff:.2f} seconds faster ({percentage:.1f}% faster)")
    else:
        percentage = ((mini_time - nano_time) / mini_time) * 100
        print(f"  {faster_model} is {time_diff:.2f} seconds faster ({percentage:.1f}% faster)")

    # Save detailed results to file
    output_file = "timing_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "gpt-5-mini": {
                "duration": mini_time,
                "agent1_output": results["gpt-5-mini"]["results"]["agent1_output"].dict(),
                "agent2_output": results["gpt-5-mini"]["results"]["agent2_output"].dict()
            },
            "gpt-5-nano": {
                "duration": nano_time,
                "agent1_output": results["gpt-5-nano"]["results"]["agent1_output"].dict(),
                "agent2_output": results["gpt-5-nano"]["results"]["agent2_output"].dict()
            },
            "summary": {
                "faster_model": faster_model,
                "time_difference_seconds": time_diff,
                "percentage_faster": percentage
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n" + "="*60)


if __name__ == "__main__":
    compare_models()
