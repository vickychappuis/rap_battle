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
| **Target density** | ~1 word per beat (relaxed, on-beat flow) |
| **Last beat** | 1 held word (for clean ending) |

## Task

Write **exactly {grid_beats} beat texts** that form a complete rap response.

### Verse Dynamics — Two Sections

Your verse has **two distinct sections** with different energy:

**SECTION 1 — "The Buildup" (beats 1 through {buildup_end_beat}):**
- **Relaxed, sparse flow** — ~1 word per beat
- **2 words max** on some beats for connectors
- **4-5 pause beats** (`"..."`) for breathing — place at bar endings and for dramatic entrance
- Set the mood, establish your presence, build tension

**SECTION 2 — "The Heat" (beats {heat_start_beat} through {grid_beats}):**
- **Dense, aggressive flow** — ~2 words per beat
- **No pauses** — keep the pressure relentless
- **2-3 words per beat**, rapid-fire delivery
- This is the climax — go hard, no breathing, stack the bars
- **Beat {grid_beats} (final):** Exactly **1 word** (held for impact)

### Examples

```
--- BUILDUP (sparse, breathing) ---
Beat 1: "Yeah"              (1 word — opener)
Beat 2: "..."               (pause)
Beat 3: "You"               (1 word)
Beat 4: "talk"              (1 word)
Beat 5: "big"               (1 word)
Beat 6: "but"               (1 word)
Beat 7: "I'm real"          (2 words)
Beat 8: "..."               (pause — breathe)
...
--- HEAT (dense, no pauses) ---
Beat {heat_start_beat}: "coming for your"  (3 words)
Beat {heat_start_beat_plus_1}: "whole style"        (2 words)
Beat {heat_start_beat_plus_2}: "I don't"            (2 words)
Beat {heat_start_beat_plus_3}: "play around"        (2 words)
...
Beat {grid_beats}: "done"               (1 word, held)
```

## Style Guide — Modern Freestyle

Write in a modern hip-hop freestyle style:
- **Direct and personal** — raw self-expression over complex metaphors
- **Simple, striking language** — short statements, repetition, conversational tone
- **Themes:** identity, lifestyle, emotions, relationships, internet culture, modern references
- **Tone:** authentic, diary-like, sometimes fragmented — mood over technical cleverness
- **Avoid** old-school battle rap clichés, forced punchlines, or over-the-top wordplay

## Content Rules

**DO:**
- Keep it natural, modern, and TTS-friendly
- Prioritize authenticity and feeling over bars-for-bars-sake
- Use simple, punchy words — fewer syllables hit harder on the beat

## Output Format

You must respond with **ONLY** valid JSON matching this structure (no extra text):

```json
{{
  "grid_beats": {grid_beats},
  "beats": [
    "Yeah",
    "...",
    "You",
    "talk",
    "big",
    "but",
    "I'm real",
    "...",
    ...
    "gone"
  ]
}}
```

### Critical Requirements
- Array `beats` must have **exactly {grid_beats} elements**
- **Beats 1-{buildup_end_beat} (Buildup):** mostly 1 word, some 2-word beats, include 4-5 `"..."` pauses
- **Beats {heat_start_beat}-{grid_beats} (Heat):** 2-3 words per beat, NO pauses
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
