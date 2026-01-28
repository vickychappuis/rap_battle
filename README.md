# Rap Battle Multi-Agent System

A minimal proof-of-concept (PoC) system using LangChain + OpenAI API for generating timed rap a cappella responses.

## Overview

This system generates battle rap responses that fit precise timing constraints:

1. **Lyricist Agent (LLM)**: Generates original rap lyrics with exact word counts to match BPM and time constraints
2. **Grid Builder (Python)**: Creates a beat-by-beat performance grid and TTS-ready prompt using deterministic logic

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key
- `BPM`: Beats per minute (e.g., `90`)
- `SECONDS_LENGTH_OF_ANSWER`: Duration in seconds (e.g., `10`)
- `OPPONENT_BARS`: The opponent's rap bars to respond to

### Optional (with defaults)
- `OPENAI_MODEL`: Default `"gpt-4o-mini"` (can use `"gpt-4"`, `"gpt-4-turbo"`, etc.)
- `TIME_SIGNATURE`: Default `"4/4"`
- `WORDS_PER_BEAT`: Default `"2"` (8th-note feel)
- `HOLD_LAST_BEAT`: Default `"1"` (final beat is a single held word)
- `CLEAN_MODE`: Default `"1"` (avoid profanity for TTS friendliness)

## Usage

### Basic Example

```bash
export OPENAI_API_KEY="sk-your-key-here"
export BPM=90
export SECONDS_LENGTH_OF_ANSWER=10
export OPPONENT_BARS="Your rhymes are weak, your flow is slow, step aside and watch a pro go"

python main.py
```

### Example with .env file

Create a `.env` file:
```
OPENAI_API_KEY=sk-your-key-here
BPM=90
SECONDS_LENGTH_OF_ANSWER=10
OPPONENT_BARS=Your rhymes are weak, your flow is slow, step aside and watch a pro go
```

Then run:
```bash
python -c "from dotenv import load_dotenv; load_dotenv()" && python main.py
```

Or use this helper script:

```bash
#!/bin/bash
# run.sh
set -a
source .env
set +a
python main.py
```

## How It Works

### 1. Timing Calculations

The orchestrator computes:
- `grid_beats = floor(BPM * seconds / 60)` - Total beats available
- `full_bars = grid_beats // 4` - Number of complete 4-beat bars
- `tail_beats = grid_beats % 4` - Remaining beats
- `total_word_budget = 2 * (grid_beats - 1) + 1` - Total words (2 per beat, except last beat)

**Example**: 90 BPM, 10 seconds
- `grid_beats = floor(90 * 10 / 60) = 15`
- `full_bars = 15 // 4 = 3`
- `tail_beats = 15 % 4 = 3`
- `total_word_budget = 2 * 14 + 1 = 29`
- Each full bar: 8 words (4 beats × 2 words/beat)
- Tail: 5 words (3 beats: 2+2+1 held)

### 2. Lyricist Agent (LLM)

Generates structured lyrics:
```json
{
  "grid_beats": 15,
  "full_bars": 3,
  "tail_beats": 3,
  "bars": [
    "You talk big game but you lack the skill",
    "I bring the heat make the crowd feel chill",
    "Your rhymes are stale mine are fresh and real"
  ],
  "tail": "Watch me climb to the",
  "final_held_word": "top"
}
```

**Validation**:
- Each bar must be exactly 8 words
- Tail must match calculated word count
- Final held word must be a single word

### 3. Grid Builder (Python Function)

Creates performance grid and TTS prompt using deterministic logic:
```json
{
  "ms_per_beat": 666.67,
  "performance_grid": [
    {"beat": 1, "bar": 1, "beat_in_bar": 1, "text": "You talk"},
    {"beat": 2, "bar": 1, "beat_in_bar": 2, "text": "big game"},
    ...
    {"beat": 15, "bar": 4, "beat_in_bar": 3, "text": "top"}
  ],
  "plain_take": "You talk big game but you lack the skill...",
  "tts_prompt": "Original male rap acapella ONLY. 90 BPM, 4/4..."
}
```

## Output Example

```
=== TIMING CALCULATIONS ===
BPM: 90
Seconds: 10.0
Total beats (exact): 15.00
Grid beats (floor): 15
Full bars: 3
Tail beats: 3
Words per beat: 2
Total word budget: 29
Per full bar words: 8
Tail words: 5
===========================

📝 Lyricist: Generating lyrics...
✓ Lyricist complete

=== LYRICIST OUTPUT (Lyrics) ===
{
  "grid_beats": 15,
  "full_bars": 3,
  "tail_beats": 3,
  "bars": [
    "Step back watch me dismantle your weak flow",
    "My bars hit harder yours move way too slow",
    "I elevate the game you just status quo"
  ],
  "tail": "Now witness greatness here I",
  "final_held_word": "go"
}

🔍 Validating Lyricist output...
✓ Validation passed: 3 bars, 5 tail words

🎵 Grid Builder: Building performance grid...
✓ Grid Builder complete

=== FINAL TTS PROMPT ===
Original male rap acapella ONLY. 90 BPM, 4/4. Length: 10.0s (exact), deliver as one clean take.

Performance grid (exact timing):
Beat 1 (Bar 1, beat 1): Step back
Beat 2 (Bar 1, beat 2): watch me
Beat 3 (Bar 1, beat 3): dismantle your
Beat 4 (Bar 1, beat 4): weak flow
...
Beat 15 (Bar 4, beat 3): go [HOLD]

Clean take:
Step back watch me dismantle your weak flow My bars hit harder yours move way too slow I elevate the game you just status quo Now witness greatness here I go
========================
```

## Architecture

### File Structure
```
rap_battle/
├── main.py                      # Main orchestrator
├── grid_builder_python.py       # Grid Builder implementation (pure Python)
├── models.py                    # Pydantic models for outputs
├── prompts/
│   ├── __init__.py              # Prompts package initialization
│   └── lyricist_prompt.py       # Lyricist prompt template
├── tests/
│   ├── __init__.py
│   └── test_timing.py           # Timing calculation tests (no API key required)
├── changes_documentation/
│   ├── QUICKSTART.md            # Quick start guide
│   └── RESTRUCTURING.md         # Restructuring documentation
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment configuration
├── run_example.sh               # Convenience script for running with .env
├── AGENTS.md                    # Project architecture overview
└── README.md                    # This file
```

### Key Components

1. **Pydantic Models**: Type-safe schemas for outputs
   - `LyricistOutput`: Lyrics structure
   - `GridBuilderOutput`: Performance grid structure
   - `PerformanceBeat`: Single beat in grid

2. **Validation Utilities**: Ensure word counts and structure correctness
   - `count_words()`: Word counting
   - `validate_lyricist_output()`: Verify bars and tail

3. **Lyricist Prompt**: Detailed instructions for the LLM agent
   - `prompts/lyricist_prompt.py`: Lyricist instructions and metadata

4. **Grid Builder**: Pure Python implementation
   - `grid_builder_python.py`: Deterministic beat-by-beat grid construction
   - No LLM calls - instant execution

5. **Orchestrator**: `RapBattleOrchestrator` class
   - Loads environment variables
   - Computes timing constraints
   - Executes Lyricist agent and Grid Builder
   - Validates outputs
   - Displays results

## Extending the System

### Different Speeds/Densities

Adjust `WORDS_PER_BEAT`:
```bash
export WORDS_PER_BEAT=1  # Slower, more deliberate (quarter notes)
export WORDS_PER_BEAT=4  # Faster, more dense (16th notes)
```

### Longer Responses

Increase duration:
```bash
export SECONDS_LENGTH_OF_ANSWER=20  # 20-second response
```

### Different BPM

```bash
export BPM=120  # Faster tempo
export BPM=70   # Slower tempo
```

### Custom Time Signatures

```bash
export TIME_SIGNATURE="3/4"  # Waltz time (would require code changes)
```

## Design Decisions

1. **Python Grid Building**: Grid Builder replaced with pure Python for instant, deterministic execution (no LLM needed)
2. **Creative Lyrics**: Lyricist uses temperature=0.7 for variation
3. **JSON Output**: Structured data for easy parsing and validation
4. **Pydantic Validation**: Type safety and automatic validation
5. **Clean Mode**: Default to TTS-friendly content
6. **Last Beat Hold**: Creates natural ending cadence

## Future Extensions

- [ ] Support for different time signatures
- [ ] Multi-voice battles (back-and-forth)
- [ ] Rhyme scheme enforcement
- [ ] Style/persona customization
- [ ] Direct TTS integration
- [ ] Audio output generation
- [ ] Web UI for interactive battles

## Troubleshooting

### "OPENAI_API_KEY environment variable is required"
Set your API key:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### "Expected X beats, got Y"
The Lyricist didn't follow beat count constraints. This is rare but can happen. The system will automatically pad or truncate within a small tolerance. If the difference is too large, try:
1. Running again (may work due to temperature)
2. Adjusting BPM or seconds for cleaner math
3. Using a more capable model (e.g., gpt-4)

### API Rate Limits
If you hit rate limits, add delays or use a different model tier.

## License

MIT
