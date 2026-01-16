#!/usr/bin/env python3
"""
Minimal PoC: Multi-Agent Rap Battle Response System
Using LangChain + OpenAI API

Two agents:
1. Lyricist: Generates timed battle-style response lyrics
2. Grid Builder: Creates performance grid and TTS prompt

Usage:
    export OPENAI_API_KEY="your-key"
    export ELEVENLABS_API_KEY="your-key"
    export BPM=90
    export SECONDS_LENGTH_OF_ANSWER=10

    # Option 1: Provide opponent bars as text
    export OPPONENT_BARS="Your rhymes are weak, your flow is slow"
    python main.py

    # Option 2: Transcribe from audio file
    export OPPONENT_AUDIO_PATH="path/to/opponent.wav"
    python main.py

    # Option 3: Record live from microphone
    export RECORD_OPPONENT_BARS=true
    export RECORD_DURATION=10  # optional, defaults to 10 seconds
    python main.py
"""

import os
import json
import math
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import requests
from pydantic import BaseModel, Field, field_validator
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import prompts from prompts module
from prompts import LYRICIST_PROMPT_TEMPLATE, GRID_BUILDER_PROMPT_TEMPLATE
from stt import record_and_transcribe, transcribe_audio


# ============================================================================
# CONSTANTS
# ============================================================================

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/music/detailed"


# ============================================================================
# PYDANTIC MODELS (Agent Output Schemas)
# ============================================================================

class LyricistOutput(BaseModel):
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


class GridBuilderOutput(BaseModel):
    """Schema for Grid Builder agent output"""
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


def validate_lyricist_output(output: LyricistOutput, expected_beats: int) -> None:
    """Validate Lyricist output matches constraints"""
    # Check beat count
    if len(output.beats) != expected_beats:
        raise ValueError(
            f"Expected {expected_beats} beats, got {len(output.beats)}"
        )

    # Count total words
    total_words = sum(len(beat.split()) for beat in output.beats)

    print(f"✓ Validation passed: {expected_beats} beats, {total_words} total words")


# ============================================================================
# ELEVENLABS MUSIC GENERATION
# ============================================================================

def generate_music(tts_prompt: str, seconds: float, api_key: str) -> str:
    """
    Generate music using ElevenLabs API

    Args:
        tts_prompt: The formatted TTS prompt from Agent 2
        seconds: Duration of the music in seconds
        api_key: ElevenLabs API key

    Returns:
        str: Path to the saved MP3 file

    Raises:
        Exception: If API call fails or response is invalid
    """
    # Prepare output directory
    output_dir = Path("music_output")
    output_dir.mkdir(exist_ok=True)

    # Generate timestamp filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"rap_battle_{timestamp}.mp3"

    # Request headers
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    # Request body
    payload = {
        "prompt": tts_prompt,
        "music_length_ms": int(seconds * 1000)
    }

    print(f"🎵 Calling ElevenLabs API...")
    print(f"   Prompt: {tts_prompt[:100]}...")
    print(f"   Duration: {seconds}s ({payload['music_length_ms']}ms)")

    try:
        # Make API request
        response = requests.post(ELEVENLABS_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        # Save audio file
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"✓ Music generated successfully: {output_path}")
        return str(output_path)

    except requests.exceptions.RequestException as e:
        error_msg = f"ElevenLabs API error: {str(e)}"
        if hasattr(e.response, 'text'):
            error_msg += f"\nResponse: {e.response.text}"
        raise Exception(error_msg)


# ============================================================================
# LYRICIST AGENT
# ============================================================================

def create_lyricist_agent(model_name: str = "gpt-4o-mini"):
    """Create the Lyricist agent"""
    parser = PydanticOutputParser(pydantic_object=LyricistOutput)

    prompt = ChatPromptTemplate.from_template(LYRICIST_PROMPT_TEMPLATE)

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
# GRID BUILDER AGENT
# ============================================================================

def create_grid_builder_agent(model_name: str = "gpt-4o-mini"):
    """Create the Grid Builder agent"""
    parser = PydanticOutputParser(pydantic_object=GridBuilderOutput)

    prompt = ChatPromptTemplate.from_template(GRID_BUILDER_PROMPT_TEMPLATE)

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

        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")

        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        # Required params
        self.bpm = int(os.environ.get("BPM", 0))
        self.seconds = float(os.environ.get("SECONDS_LENGTH_OF_ANSWER", 0))

        if not self.bpm or not self.seconds:
            raise ValueError("Required env vars: BPM, SECONDS_LENGTH_OF_ANSWER")

        # Get opponent bars from one of three sources (priority order):
        # 1. Text (OPPONENT_BARS)
        # 2. Audio file (OPPONENT_AUDIO_PATH)
        # 3. Live recording (RECORD_OPPONENT_BARS=true)
        self.opponent_bars = self._get_opponent_bars()

        # Compute timing constraints
        self._compute_timing()

        # Create agents
        self.lyricist_chain, self.lyricist_parser = create_lyricist_agent(self.model)
        self.grid_builder_chain, self.grid_builder_parser = create_grid_builder_agent(self.model)

    def _get_opponent_bars(self) -> str:
        """
        Get opponent bars from text, audio file, or live recording.

        Priority:
        1. RECORD_OPPONENT_BARS=true (record from microphone)
        2. OPPONENT_BARS env var (direct text)
        3. OPPONENT_AUDIO_PATH env var (transcribe audio file)

        Returns:
            Transcribed or provided opponent bars text

        Raises:
            ValueError: If no input source is provided
        """
        # Option 1: Record from microphone
        record_enabled = os.environ.get("RECORD_OPPONENT_BARS", "").lower() in ("true", "1", "yes")
        if record_enabled:
            record_duration = float(os.environ.get("RECORD_DURATION", "10"))
            print(f"Recording opponent bars for {record_duration} seconds...")
            return record_and_transcribe(record_duration)

        # Option 2: Direct text input
        opponent_bars = os.environ.get("OPPONENT_BARS", "").strip()
        if opponent_bars:
            print("Using opponent bars from OPPONENT_BARS env var")
            return opponent_bars

        # Option 3: Transcribe from audio file
        audio_path = os.environ.get("OPPONENT_AUDIO_PATH", "").strip()
        if audio_path:
            print(f"Transcribing opponent bars from audio file: {audio_path}")
            return transcribe_audio(audio_path)

        raise ValueError(
            "No opponent input provided. Set one of: "
            "OPPONENT_BARS (text), OPPONENT_AUDIO_PATH (file), or RECORD_OPPONENT_BARS=true"
        )

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

        # Step 1: Invoke the Lyricist
        print("📝 Lyricist: Generating beat-by-beat lyrics...")

        lyricist_input = {
            "opponent_bars": self.opponent_bars,
            "bpm": self.bpm,
            "seconds": self.seconds,
            "grid_beats": self.grid_beats,
            "grid_beats_minus_1": self.grid_beats - 1,
            "format_instructions": self.lyricist_parser.get_format_instructions()
        }

        lyricist_output = self.lyricist_chain.invoke(lyricist_input)

        print("✓ Lyricist complete\n")
        print("=== LYRICIST OUTPUT (Beat-by-Beat Lyrics) ===")
        print(json.dumps(lyricist_output.model_dump(), indent=2))
        print("=============================================\n")

        # Step 2: Validate Lyricist output
        print("🔍 Validating Lyricist output...")
        validate_lyricist_output(lyricist_output, self.grid_beats)
        print()

        # Step 3: Invoke Grid Builder
        print("🎵 Grid Builder: Building performance grid...")

        grid_builder_input = {
            "lyricist_json": json.dumps(lyricist_output.model_dump(), indent=2),
            "bpm": self.bpm,
            "seconds": self.seconds,
            "format_instructions": self.grid_builder_parser.get_format_instructions()
        }

        grid_builder_output = self.grid_builder_chain.invoke(grid_builder_input)

        print("✓ Grid Builder complete\n")
        print("=== GRID BUILDER OUTPUT (Performance Grid) ===")
        print(json.dumps(grid_builder_output.model_dump(), indent=2))
        print("===============================================\n")

        # Step 4: Display final TTS prompt
        print("=== FINAL TTS PROMPT ===")
        print(grid_builder_output.tts_prompt)
        print("========================\n")

        # Step 5: Generate music using ElevenLabs
        print("🎼 Step 3: Generating music with ElevenLabs...")
        input("Press Enter to call ElevenLabs API (or Ctrl+C to cancel)...")
        try:
            music_file_path = generate_music(
                tts_prompt=grid_builder_output.tts_prompt,
                seconds=self.seconds,
                api_key=self.elevenlabs_api_key
            )
            print(f"✓ Music file saved: {music_file_path}\n")
        except Exception as e:
            print(f"⚠️  Music generation failed: {e}")
            print("   Continuing without audio output...\n")
            music_file_path = None

        print("✓ Pipeline complete!")

        return {
            "lyricist_output": lyricist_output,
            "grid_builder_output": grid_builder_output,
            "music_file_path": music_file_path
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
