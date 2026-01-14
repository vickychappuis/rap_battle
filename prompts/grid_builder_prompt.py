"""
Grid Builder Prompt Template

This agent creates performance grids and TTS-ready prompts from lyrics.
"""

GRID_BUILDER_PROMPT_TEMPLATE = """# Performance Grid & TTS Prompt Builder

You are a performance grid and TTS prompt builder for rap delivery. The Lyricist has already structured the lyrics beat-by-beat. Your job is to format them for TTS.

## Input Data (Lyricist Output - Beat-by-Beat)

```json
{lyricist_json}
```

## Timing Parameters

| Parameter | Value |
|-----------|-------|
| **BPM** | {bpm} |
| **Total seconds** | {seconds} |

## Your Tasks

### 1. Calculate Timing
- `ms_per_beat = 60000 / BPM`

### 2. Build Performance Grid
Take the beat texts from the Lyricist and create a `performance_grid`:

**For each beat:**
- `beat`: Beat number (1-indexed, from 1 to grid_beats)
- `bar`: Bar number (1-indexed, beat ÷ 4, rounded up)
- `beat_in_bar`: Position within bar (1-4, calculated as: ((beat-1) % 4) + 1)
- `text`: The beat text from the Lyricist's `beats` array

**Example:**
```
Beat 1 → bar=1, beat_in_bar=1, text=beats[0]
Beat 2 → bar=1, beat_in_bar=2, text=beats[1]
Beat 5 → bar=2, beat_in_bar=1, text=beats[4]
```

### 3. Create Plain Take
- Join all beat texts with spaces
- This is the complete lyrics as one string

### 4. Create TTS Prompt
Format the final TTS prompt as:

```
Original male rap acapella ONLY. {{BPM}} BPM, 4/4. Length: {{SECONDS}}s (exact), deliver as one clean take.

Performance grid (exact timing):
Beat 1 (Bar 1, beat 1): {{beat_text_1}}
Beat 2 (Bar 1, beat 2): {{beat_text_2}}
...

Clean take:
{{plain_take}}
```

## Output Format

You must respond with **ONLY** valid JSON matching this structure (no extra text):

```json
{{
  "ms_per_beat": 666.67,
  "performance_grid": [
    {{"beat": 1, "bar": 1, "beat_in_bar": 1, "text": "You say"}},
    {{"beat": 2, "bar": 1, "beat_in_bar": 2, "text": "you're pro but"}},
    ...
  ],
  "plain_take": "You say you're pro but I'm the one winning...",
  "tts_prompt": "Original male rap acapella ONLY..."
}}
```

### Critical Requirements
- Calculate `ms_per_beat` correctly
- Map every beat from the Lyricist's output
- Calculate bar numbers correctly (beat ÷ 4, rounded up)
- Return **ONLY** the JSON object, no other text

{format_instructions}
"""

# Agent metadata
GRID_BUILDER_METADATA = {
    "name": "Grid Builder",
    "description": "Creates performance grid and TTS-ready prompts",
    "temperature": 0.0,
    "default_model": "gpt-4o-mini"
}
