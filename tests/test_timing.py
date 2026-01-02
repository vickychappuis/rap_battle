#!/usr/bin/env python3
"""
Test script to validate timing calculations without calling OpenAI API
Useful for testing the math and understanding the system
"""

import math


def compute_timing(bpm: int, seconds: float, words_per_beat: int = 2):
    """Compute timing constraints for rap battle"""

    # Total beats available
    total_beats_exact = bpm * seconds / 60.0
    grid_beats = math.floor(total_beats_exact)

    # Split into full bars (4 beats each) and tail
    full_bars = grid_beats // 4
    tail_beats = grid_beats % 4

    # Word budget calculation
    # All beats except the last use words_per_beat
    # Last beat uses 1 word (held)
    total_word_budget = words_per_beat * (grid_beats - 1) + 1

    # Words per full bar
    per_full_bar_words = 4 * words_per_beat

    # Tail words = total budget - (full bars * words per bar)
    tail_words = total_word_budget - (full_bars * per_full_bar_words)

    # Milliseconds per beat
    ms_per_beat = 60000 / bpm

    return {
        "bpm": bpm,
        "seconds": seconds,
        "total_beats_exact": total_beats_exact,
        "grid_beats": grid_beats,
        "full_bars": full_bars,
        "tail_beats": tail_beats,
        "words_per_beat": words_per_beat,
        "total_word_budget": total_word_budget,
        "per_full_bar_words": per_full_bar_words,
        "tail_words": tail_words,
        "ms_per_beat": ms_per_beat,
    }


def print_timing_table():
    """Print timing calculations for various BPM/duration combinations"""

    test_cases = [
        (90, 10),   # Standard case
        (120, 10),  # Faster tempo, same duration
        (90, 15),   # Same tempo, longer duration
        (80, 8),    # Slower tempo, shorter duration
        (100, 12),  # Even BPM, even duration
    ]

    print("=" * 80)
    print("TIMING CALCULATIONS FOR VARIOUS BPM/DURATION COMBINATIONS")
    print("=" * 80)

    for bpm, seconds in test_cases:
        result = compute_timing(bpm, seconds)

        print(f"\n{'─' * 80}")
        print(f"BPM: {result['bpm']} | Seconds: {result['seconds']}")
        print(f"{'─' * 80}")
        print(f"Total beats (exact):    {result['total_beats_exact']:.2f}")
        print(f"Grid beats (floor):     {result['grid_beats']}")
        print(f"Full bars:              {result['full_bars']}")
        print(f"Tail beats:             {result['tail_beats']}")
        print(f"Words per beat:         {result['words_per_beat']}")
        print(f"Total word budget:      {result['total_word_budget']}")
        print(f"Per full bar words:     {result['per_full_bar_words']}")
        print(f"Tail words:             {result['tail_words']}")
        print(f"Milliseconds per beat:  {result['ms_per_beat']:.2f}")

        # Show structure
        print(f"\nStructure:")
        print(f"  - {result['full_bars']} full bars × {result['per_full_bar_words']} words each = {result['full_bars'] * result['per_full_bar_words']} words")
        print(f"  - 1 tail section = {result['tail_words']} words")
        print(f"  - Total: {result['full_bars'] * result['per_full_bar_words'] + result['tail_words']} words")

        # Breakdown of tail
        if result['tail_beats'] > 0:
            tail_breakdown = []
            for i in range(result['tail_beats']):
                if i == result['tail_beats'] - 1:  # Last beat
                    tail_breakdown.append("1 word (held)")
                else:
                    tail_breakdown.append(f"{result['words_per_beat']} words")
            print(f"\nTail breakdown ({result['tail_beats']} beats):")
            for i, words in enumerate(tail_breakdown):
                print(f"  Beat {i+1}: {words}")

    print(f"\n{'=' * 80}\n")


def test_word_distribution(bpm: int = 90, seconds: float = 10):
    """Show example word distribution across beats"""

    result = compute_timing(bpm, seconds)

    print(f"\n{'=' * 80}")
    print(f"EXAMPLE WORD DISTRIBUTION: {bpm} BPM, {seconds}s")
    print(f"{'=' * 80}\n")

    # Generate example bars
    bars = []
    for i in range(result['full_bars']):
        bar_words = [f"word{j+1}" for j in range(result['per_full_bar_words'])]
        bars.append(" ".join(bar_words))

    # Generate tail
    tail_words = [f"tail{j+1}" for j in range(result['tail_words'])]
    tail = " ".join(tail_words)

    print("Full bars:")
    for i, bar in enumerate(bars):
        print(f"  Bar {i+1}: {bar}")

    print(f"\nTail: {tail}")

    print(f"\nBeat-by-beat breakdown:")
    beat_num = 1

    # Process full bars
    for bar_idx, bar in enumerate(bars):
        words = bar.split()
        for beat_in_bar in range(4):
            start_idx = beat_in_bar * result['words_per_beat']
            end_idx = start_idx + result['words_per_beat']
            beat_words = " ".join(words[start_idx:end_idx])
            print(f"  Beat {beat_num:2d} (Bar {bar_idx+1}, beat {beat_in_bar+1}): {beat_words}")
            beat_num += 1

    # Process tail
    if result['tail_beats'] > 0:
        tail_words_list = tail.split()
        word_idx = 0
        for beat_in_tail in range(result['tail_beats']):
            if beat_in_tail == result['tail_beats'] - 1:  # Last beat
                beat_words = tail_words_list[word_idx]
                print(f"  Beat {beat_num:2d} (Tail, beat {beat_in_tail+1}): {beat_words} [HELD]")
            else:
                beat_words = " ".join(tail_words_list[word_idx:word_idx + result['words_per_beat']])
                print(f"  Beat {beat_num:2d} (Tail, beat {beat_in_tail+1}): {beat_words}")
                word_idx += result['words_per_beat']
            beat_num += 1

    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    print("\n🎵 Rap Battle Timing Calculator 🎵\n")

    # Show timing table
    print_timing_table()

    # Show detailed word distribution
    test_word_distribution(90, 10)

    # Show another example
    test_word_distribution(120, 15)
