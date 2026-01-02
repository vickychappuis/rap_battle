#!/usr/bin/env python3
"""
Minimal PoC: Multi-Agent Rap Battle Response System
Using LangChain + OpenAI API

Two agents:
1. Lyricist: Generates timed battle-style response lyrics
2. Grid + TTS Builder: Creates performance grid and TTS prompt

Usage:
    export OPENAI_API_KEY="your-key"
    export BPM=90
    export SECONDS_LENGTH_OF_ANSWER=10
    export OPPONENT_BARS="Your rhymes are weak, your flow is slow, step aside and watch a pro go"
    python main.py
"""

import os
import json
import math
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import prompts from prompts module
from prompts import AGENT1_PROMPT_TEMPLATE, AGENT2_PROMPT_TEMPLATE


# ============================================================================
# PYDANTIC MODELS (Agent Output Schemas)
# ============================================================================

class Agent1Output(BaseModel):
    """Schema for Lyricist agent output - beat-based format"""
    grid_beats: int = Field(description="Total beats in the response")
    beats: List[str] = Field(description="List of beat texts, one per beat")

    @field_validator('beats')
    @classmethod
    def validate_beats(cls, v, info):
        """Validate beat list matches grid_beats and word counts"""
        grid_beats = info.data.get('grid_beats')

        # Check beat count matches grid_beats
        if len(v) != grid_beats:
            raise ValueError(f"Expected {grid_beats} beats, got {len(v)}")

        # Check word count per beat
        for i, beat in enumerate(v):
            word_count = len(beat.split())

            # Last beat must be exactly 1 word (held)
            if i == len(v) - 1:
                if word_count != 1:
                    raise ValueError(f"Final beat must be exactly 1 word, got {word_count}: '{beat}'")
            else:
                # Other beats should be 1-3 words
                if word_count < 1 or word_count > 3:
                    raise ValueError(f"Beat {i+1} has {word_count} words, expected 1-3 words")

        return v


class PerformanceBeat(BaseModel):
    """Single beat in the performance grid"""
    beat: int = Field(description="Beat number (1-indexed)")
    bar: int = Field(description="Bar number (1-indexed)")
    beat_in_bar: int = Field(description="Beat within the bar (1-4)")
    text: str = Field(description="Text to deliver on this beat")


class Agent2Output(BaseModel):
    """Schema for Grid + TTS Builder agent output"""
    ms_per_beat: float = Field(description="Milliseconds per beat")
    performance_grid: List[PerformanceBeat] = Field(description="Beat-by-beat performance grid")
    plain_take: str = Field(description="Single concatenated text in delivery order")
    tts_prompt: str = Field(description="Final TTS prompt string")


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())


def validate_agent1_output(output: Agent1Output, expected_beats: int) -> None:
    """Validate Agent 1 output matches constraints"""
    # Check beat count
    if len(output.beats) != expected_beats:
        raise ValueError(
            f"Expected {expected_beats} beats, got {len(output.beats)}"
        )

    # Count total words
    total_words = sum(len(beat.split()) for beat in output.beats)

    print(f"✓ Validation passed: {expected_beats} beats, {total_words} total words")


# ============================================================================
# AGENT 1: LYRICIST
# ============================================================================

def create_lyricist_agent(model_name: str = "gpt-4o-mini"):
    """Create Agent 1: Lyricist"""
    parser = PydanticOutputParser(pydantic_object=Agent1Output)

    prompt = ChatPromptTemplate.from_template(AGENT1_PROMPT_TEMPLATE)

    llm = ChatOpenAI(
        model="gpt-5-mini",
        reasoning={"effort": "low"},      # optional: add "summary": "auto"
        output_version="responses/v1",    # keep reasoning blocks in message content
        temperature=0.7,  # Some creativity, but controlled
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    chain = prompt | llm | parser

    return chain, parser


# ============================================================================
# AGENT 2: GRID + TTS PROMPT BUILDER
# ============================================================================

def create_grid_builder_agent(model_name: str = "gpt-4o-mini"):
    """Create Agent 2: Grid + TTS Prompt Builder"""
    parser = PydanticOutputParser(pydantic_object=Agent2Output)

    prompt = ChatPromptTemplate.from_template(AGENT2_PROMPT_TEMPLATE)

    llm = ChatOpenAI(
        model="gpt-5-mini",
        reasoning={"effort": "low"},      # optional: add "summary": "auto"
        output_version="responses/v1",    # keep reasoning blocks in message content
        temperature=0,  # Deterministic for grid building
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    chain = prompt | llm | parser

    return chain, parser


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class RapBattleOrchestrator:
    """Main orchestrator for the rap battle system"""

    def __init__(self):
        # Load environment variables
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        # Required params
        self.bpm = int(os.environ.get("BPM", 0))
        self.seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 0))
        self.opponent_bars = os.environ.get("OPPONENT_BARS", "")

        if not self.bpm or not self.seconds or not self.opponent_bars:
            raise ValueError(
                "Required env vars: BPM, SECONDS_LENGTH_OF_ANSWER, OPPONENT_BARS"
            )

        # Compute timing constraints
        self._compute_timing()

        # Create agents
        self.agent1_chain, self.agent1_parser = create_lyricist_agent(self.model)
        self.agent2_chain, self.agent2_parser = create_grid_builder_agent(self.model)

    def _compute_timing(self):
        """Compute timing constraints"""
        # Total beats available
        total_beats_exact = self.bpm * self.seconds / 60.0
        self.grid_beats = math.floor(total_beats_exact)

        print(f"\n=== TIMING CALCULATIONS ===")
        print(f"BPM: {self.bpm}")
        print(f"Seconds: {self.seconds}")
        print(f"Total beats (exact): {total_beats_exact:.2f}")
        print(f"Grid beats: {self.grid_beats}")
        print(f"Target: 1-3 words per beat (aim for ~2)")
        print(f"Final beat: 1 held word")
        print(f"===========================\n")

    def run(self):
        """Execute the full pipeline"""
        print("🎤 Starting Rap Battle Response Generator...\n")

        # Step 1: Invoke Agent 1 (Lyricist)
        print("📝 Agent 1 (Lyricist): Generating beat-by-beat lyrics...")

        agent1_input = {
            "opponent_bars": self.opponent_bars,
            "bpm": self.bpm,
            "seconds": self.seconds,
            "grid_beats": self.grid_beats,
            "grid_beats_minus_1": self.grid_beats - 1,
            "format_instructions": self.agent1_parser.get_format_instructions()
        }

        agent1_output = self.agent1_chain.invoke(agent1_input)

        print("✓ Agent 1 complete\n")
        print("=== AGENT 1 OUTPUT (Beat-by-Beat Lyrics) ===")
        print(json.dumps(agent1_output.model_dump(), indent=2))
        print("=============================================\n")

        # Step 2: Validate Agent 1 output
        print("🔍 Validating Agent 1 output...")
        validate_agent1_output(agent1_output, self.grid_beats)
        print()

        # Step 3: Invoke Agent 2 (Grid + TTS Builder)
        print("🎵 Agent 2 (Grid + TTS Builder): Building performance grid...")

        agent2_input = {
            "agent1_json": json.dumps(agent1_output.model_dump(), indent=2),
            "bpm": self.bpm,
            "seconds": self.seconds,
            "format_instructions": self.agent2_parser.get_format_instructions()
        }

        agent2_output = self.agent2_chain.invoke(agent2_input)

        print("✓ Agent 2 complete\n")
        print("=== AGENT 2 OUTPUT (Performance Grid) ===")
        print(json.dumps(agent2_output.model_dump(), indent=2))
        print("==========================================\n")

        # Step 4: Display final TTS prompt
        print("=== FINAL TTS PROMPT ===")
        print(agent2_output.tts_prompt)
        print("========================\n")

        print("✓ Pipeline complete!")

        return {
            "agent1_output": agent1_output,
            "agent2_output": agent2_output
        }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    try:
        orchestrator = RapBattleOrchestrator()
        results = orchestrator.run()
        return results
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()


"""
EXAMPLE OUTPUT:

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

=== AGENT 1 OUTPUT (Lyrics) ===
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
================================

=== AGENT 2 OUTPUT (Performance Grid) ===
{
  "ms_per_beat": 666.67,
  "performance_grid": [
    {"beat": 1, "bar": 1, "beat_in_bar": 1, "text": "You talk"},
    {"beat": 2, "bar": 1, "beat_in_bar": 2, "text": "big game"},
    {"beat": 3, "bar": 1, "beat_in_bar": 3, "text": "but you"},
    {"beat": 4, "bar": 1, "beat_in_bar": 4, "text": "lack the"},
    {"beat": 5, "bar": 2, "beat_in_bar": 1, "text": "skill I"},
    ...
    {"beat": 15, "bar": 4, "beat_in_bar": 3, "text": "top"}
  ],
  "plain_take": "You talk big game but you lack the skill I bring the heat...",
  "tts_prompt": "Original male rap acapella ONLY. 90 BPM, 4/4. Length: 10s (exact)..."
}
==========================================
"""
