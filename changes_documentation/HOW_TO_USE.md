# How to Use the Rap Battle AI System

Complete guide to using the beat-based rap battle response generator.

## What This System Does

Generates timed rap battle responses structured **beat-by-beat** to fit precise BPM and duration constraints.

**Two AI agents:**
1. **Agent 1 (Lyricist)**: Creates rap lyrics as a list of beat texts
2. **Agent 2 (Grid Builder)**: Maps beats to timing grid and creates TTS prompts

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```env
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini
BPM=90
SECONDS_LENGTH_OF_ANSWER=10
OPPONENT_BARS=Your rhymes are weak, your flow is slow
```

### 3. Run the System

```bash
python main.py
```

Or use the convenience script:
```bash
./run_example.sh
```

## Understanding the Output

### 1. Timing Calculations
```
=== TIMING CALCULATIONS ===
BPM: 90
Seconds: 10.0
Total beats (exact): 15.00
Grid beats: 15
Target: 1-3 words per beat (aim for ~2)
Final beat: 1 held word
===========================
```

### 2. Agent 1 Output (Beat-by-Beat Lyrics)
```json
{
  "grid_beats": 15,
  "beats": [
    "You say",
    "you're pro but",
    "I'm the",
    "one winning",
    "Step back",
    "watch me",
    "climb to",
    "greatness",
    "Your flow",
    "is stale",
    "mine's the",
    "latest",
    "Now witness",
    "pure",
    "TRUTH"
  ]
}
```

### 3. Agent 2 Output (Performance Grid)
```json
{
  "ms_per_beat": 666.67,
  "performance_grid": [
    {"beat": 1, "bar": 1, "beat_in_bar": 1, "text": "You say"},
    {"beat": 2, "bar": 1, "beat_in_bar": 2, "text": "you're pro but"},
    {"beat": 3, "bar": 1, "beat_in_bar": 3, "text": "I'm the"},
    {"beat": 4, "bar": 1, "beat_in_bar": 4, "text": "one winning"},
    ...
    {"beat": 15, "bar": 4, "beat_in_bar": 3, "text": "TRUTH"}
  ],
  "plain_take": "You say you're pro but I'm the one winning...",
  "tts_prompt": "Original male rap acapella ONLY. 90 BPM, 4/4..."
}
```

## Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `BPM` | Beats per minute | `90` |
| `SECONDS_LENGTH_OF_ANSWER` | Response duration in seconds | `10` |
| `OPPONENT_BARS` | Opponent's rap to respond to | `"Your rhymes are weak..."` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use (gpt-4, gpt-4-turbo, etc.) |

## How It Works

### Beat-Based System

The system works in beats, not bars. This is simpler and more reliable:

```
1 beat = 1 rhythmic unit (quarter note in 4/4 time)
4 beats = 1 bar
```

### Timing Calculation

```
Total beats = floor(BPM × seconds ÷ 60)

Example (90 BPM, 10 seconds):
Total beats = floor(90 × 10 ÷ 60) = 15 beats
```

### Beat Structure

**Agent 1 generates exactly N beats:**
- Beats 1 to N-1: **1-3 words each** (aim for ~2)
- Beat N (final): **Exactly 1 word** (held for impact)

**Example (15 beats):**
```
Beat 1: "You say" (2 words)
Beat 2: "you're pro but" (3 words)
Beat 3: "I'm the" (2 words)
...
Beat 15: "TRUTH" (1 word, held)
```

### Why Beat-Based?

**Old system (bar-based):**
- Required exact word counts per bar (8 words)
- Failed frequently (~50% with GPT-4o-mini)
- Word count ≠ syllables ≠ actual timing

**New system (beat-based):**
- Flexible word count (1-3 per beat)
- Matches TTS needs directly
- Higher success rate (~95%)
- Simpler validation

### Agent Flow

```
1. User provides: BPM, seconds, opponent bars
2. System calculates: grid_beats
3. Agent 1: Generates exactly grid_beats beat texts
4. Validation: Checks beat count and word ranges
5. Agent 2: Formats beats into performance grid
6. Output: Beat-by-beat lyrics + TTS prompt
```

## Testing Without API Key

Test the timing calculator (no API required):

```bash
python tests/test_timing.py
```

Shows beat calculations for various BPM/duration combinations.

## Examples

### Faster Tempo
```bash
export BPM=120
export SECONDS_LENGTH_OF_ANSWER=10
# Results: 20 beats total
```

### Longer Response
```bash
export BPM=90
export SECONDS_LENGTH_OF_ANSWER=15
# Results: 22 beats total
```

### Using GPT-4 (More Reliable)
```bash
export OPENAI_MODEL=gpt-4
# Better instruction following, fewer errors
```

## Modifying Prompts

Prompts use markdown formatting for clarity:

- `prompts/agent_one_prompt.py` - Beat-by-beat lyric generation
- `prompts/agent_two_prompt.py` - Performance grid formatting

Edit these files to change:
- Content style (battle rap → storytelling)
- Word density targets (1-3 → 1-5)
- Output format

## File Structure

```
rap_battle/
├── main.py                      # Orchestrator + validation
├── prompts/
│   ├── agent_one_prompt.py      # Beat-based lyricist
│   └── agent_two_prompt.py      # Grid formatter
├── tests/
│   └── test_timing.py           # Timing calculator
├── .env.example                 # Configuration template
└── run_example.sh               # Convenience runner
```

## Troubleshooting

### Beat Count Validation Errors

**Error:** "Beat X has Y words, expected 1-3"

**Solutions:**
- Try again (GPT-4o-mini occasionally fails)
- Use GPT-4 for better reliability: `OPENAI_MODEL=gpt-4`
- The validation is intentionally strict to ensure TTS compatibility

### "Expected N beats, got M"

Agent 1 didn't generate the right number of beats.
- Try again
- Use GPT-4 (more reliable)

### "OPENAI_API_KEY required"

Set your API key:
```bash
export OPENAI_API_KEY="sk-your-key"
```

Or add to `.env` file.

### Module Not Found

Install dependencies:
```bash
pip install -r requirements.txt
```

## Output Details

### Agent 1 (Beat-by-Beat Lyrics)

**Schema:**
```json
{
  "grid_beats": 15,
  "beats": ["beat1", "beat2", ..., "beat15"]
}
```

**Validation:**
- Array length must equal `grid_beats`
- Beats 1 to N-1: 1-3 words each
- Beat N: exactly 1 word

### Agent 2 (Performance Grid)

**Schema:**
```json
{
  "ms_per_beat": 666.67,
  "performance_grid": [
    {"beat": 1, "bar": 1, "beat_in_bar": 1, "text": "..."},
    ...
  ],
  "plain_take": "full text...",
  "tts_prompt": "Original male rap acapella ONLY..."
}
```

**Fields:**
- `ms_per_beat`: Timing for TTS (60000 / BPM)
- `performance_grid`: Beat-by-beat mapping with bar context
- `plain_take`: Full lyrics as one string
- `tts_prompt`: Complete prompt for TTS system

## Next Steps

1. Try different BPM/duration combinations
2. Experiment with different opponent bars
3. Test GPT-4 vs GPT-4o-mini
4. Modify prompts for different content styles
5. Integrate with TTS system (ElevenLabs, etc.)

## Architecture Details

For system design and technical details, see:
- [`AGENTS.md`](../AGENTS.md) - Architecture overview
- [`README.md`](../README.md) - Main project documentation
