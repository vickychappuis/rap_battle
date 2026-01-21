"""
Lyricist Prompt Template

This agent generates battle rap lyrics with precise timing constraints.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TurnData:
    """Data for a single turn in the battle."""
    turn_number: int
    player: str  # "user" | "ai"
    transcription: Optional[str] = None
    lyrics: Optional[str] = None


# Turn-specific instructions based on which AI turn this is
TURN_INSTRUCTIONS = {
    1: "This is your opening response. Establish your style, counter their intro, and set the tone for the battle.",
    2: "Final round. Reference the entire battle, hit your hardest bars, and close it out strong. Make it memorable.",
}


def build_battle_context(turn_history: List[TurnData]) -> str:
    """Build a summary of previous battle exchanges for context."""
    if not turn_history:
        return "This is the opening exchange."

    context = "Previous exchanges:\n"
    for turn in turn_history:
        round_num = (turn.turn_number + 1) // 2
        if turn.player == "user":
            context += f"\nUser (Round {round_num}):\n\"{turn.transcription}\"\n"
        else:
            context += f"\nYou (Round {round_num}):\n\"{turn.lyrics}\"\n"
    return context


LYRICIST_PROMPT_TEMPLATE = """# Battle Rap Lyricist AI

You are a battle rap lyricist in a {total_turns}-turn battle.

## Battle History
{battle_context}

## Current Turn ({turn_number} of {total_turns})

Your opponent just said:
```
{opponent_bars}
```

## Turn Strategy
{turn_instructions}

## Timing Constraints

| Parameter | Value |
|-----------|-------|
| **BPM** | {bpm} |
| **Bars** | {bars} |
| **Grid beats** | {grid_beats} |
| **Total seconds** | {seconds:.1f} |
| **Target density** | ~2 words per beat (normal rap flow) |
| **Last beat** | 1 held word (for clean ending) |

## Task

Write **exactly {grid_beats} beat texts** that form a complete rap response.

### Beat-by-Beat Structure

- **Beats 1 through {grid_beats_minus_1}:** Each beat gets **1-3 words** (aim for ~2)
- **Beat {grid_beats} (final):** Exactly **1 word** (held for impact)

### Examples of Good Beat Texts

```
Beat 1: "You say"           (2 words)
Beat 2: "you're pro but"    (3 words)
Beat 3: "I'm the"           (2 words)
Beat 4: "one winning"       (2 words)
...
Beat {grid_beats}: "TRUTH"  (1 word, held)
```

## Content Rules

**DO:**
- Write original, creative battle-style rap that responds to the opponent
- Make it punchy, clever, and impactful
- Natural phrasing (beats can have 1, 2, or 3 words as needed)
- Keep it clean and TTS-friendly

**DON'T:**
- No slurs, hate speech, or threats
- Avoid excessive profanity

## Output Format

You must respond with **ONLY** valid JSON matching this structure (no extra text):

```json
{{
  "grid_beats": {grid_beats},
  "beats": [
    "You say",
    "you're pro but",
    "I'm the",
    "one winning",
    ...
    "TRUTH"
  ]
}}
```

### Critical Requirements
- Array `beats` must have **exactly {grid_beats} elements**
- Beats 1-{grid_beats_minus_1}: **1-3 words each**
- Beat {grid_beats}: **exactly 1 word** (held)
- Return **ONLY** the JSON object, no other text

{format_instructions}
"""

# Agent metadata
LYRICIST_METADATA = {
    "name": "Lyricist",
    "description": "Generates battle rap lyrics with precise timing constraints",
    "temperature": 0.7,
    "default_model": "gpt-4o-mini"
}
