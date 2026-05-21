#!/usr/bin/env python3
"""
Minimal PoC: Rap Battle Response System
Using LangChain + OpenAI API

Components:
1. Lyricist (LLM): Generates timed battle-style response lyrics
2. Grid Builder (Python): Creates performance grid and TTS prompt

Base track plays continuously throughout the battle. AI response is mixed
over the beat at the next bar boundary.

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

    # Optional: Custom base track
    export BASE_TRACK_PATH="assets/tracks/base_90bpm.wav"

    # Optional: Mock ElevenLabs API (for testing)
    export MOCK_ELEVENLABS=true
    export MOCK_RESPONSE_PATH="music_output/rap_battle_20260113_214955.mp3"
"""

import os
import json
import math
import time
import random
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import models
from models import LyricistOutput, GridBuilderOutput

# Import prompts from prompts module
from prompts import LYRICIST_PROMPT_TEMPLATE

# Import Python GridBuilder (replaces LLM-based Grid Builder agent)
from grid_builder_python import build_grid_from_lyrics


# ============================================================================
# CONSTANTS
# ============================================================================

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/music/detailed"


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_lyricist_output(output: LyricistOutput, expected_bars: int) -> None:
    """Validate and fix Lyricist output to match expected bar count.

    Lenient validation: truncates or pads bars if off by a small amount.
    """
    actual_bars = len(output.bars)

    if actual_bars > expected_bars:
        print(f"⚠ Got {actual_bars} bars, truncating to {expected_bars}")
        output.bars = output.bars[:expected_bars]
    elif actual_bars < expected_bars:
        diff = expected_bars - actual_bars
        if diff <= 2:
            print(f"⚠ Got {actual_bars} bars, padding {diff} to reach {expected_bars}")
            output.bars.extend(["yeah..."] * diff)
        else:
            raise ValueError(
                f"Expected {expected_bars} bars, got {actual_bars} (too few to pad)"
            )

    total_words = sum(len(bar.split()) for bar in output.bars)
    print(f"✓ Validation passed: {actual_bars} bars, {total_words} total words")


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

    # Request body — round up to next whole second to match the rounded TTS prompt
    # and avoid fractional durations that the model may handle awkwardly
    import math
    rounded_ms = math.ceil(seconds) * 1000
    payload = {
        "prompt": tts_prompt,
        "music_length_ms": rounded_ms
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
# ORCHESTRATOR
# ============================================================================

class RapBattleOrchestrator:
    """Main orchestrator for the rap battle system"""

    def __init__(self):
        # Lazy import for audio (requires PortAudio, not available in Docker)
        from audio_player import AudioMixer

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

        # Initialize audio mixer for base track playback (before opponent input)
        base_track_path = os.environ.get("BASE_TRACK_PATH", "assets/tracks/base_90bpm.wav")
        self.mixer = AudioMixer(base_track_path, self.bpm)

        # Opponent bars will be captured in run() after beat starts
        self.opponent_bars = None

        # Compute timing constraints
        self._compute_timing()

        # Create lyricist agent (Grid Builder is now pure Python)
        self.lyricist_chain, self.lyricist_parser = create_lyricist_agent(self.model)

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
            from stt import record_and_transcribe
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
            from stt import transcribe_audio
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
        print(f"Total beats: {self.grid_beats}")
        print(f"Total bars: {self.grid_beats // 4}")
        print(f"===========================\n")

    def run(self):
        """Execute the full pipeline"""
        print("🎤 Starting Rap Battle Response Generator...\n")

        # Load and start base track playback FIRST (beat plays during opponent input)
        self.mixer.load_base_track()
        self.mixer.start()

        try:
            # Wait for user to be ready before capturing opponent bars
            input("Press Enter when ready to record opponent bars...")

            # Step 0: Get opponent bars (recording happens with beat playing)
            self.opponent_bars = self._get_opponent_bars()

            print("=== OPPONENT BARS (STT Transcription) ===")
            print(self.opponent_bars)
            print("==========================================\n")

            # Step 1: Invoke the Lyricist
            print("📝 Lyricist: Generating bars...")
            lyricist_start = time.time()

            bars = self.grid_beats // 4
            quarter = max(1, bars // 4)
            seconds_per_bar = 4 * (60.0 / self.bpm)
            syllable_budget = self.grid_beats * 2  # ~2 syllables per beat avg

            lyricist_input = {
                "opponent_bars": self.opponent_bars,
                "bpm": self.bpm,
                "bars": bars,
                "seconds": self.seconds,
                "seconds_per_bar": seconds_per_bar,
                "syllable_budget": syllable_budget,
                "s1_end": quarter,
                "s2_start": quarter + 1,
                "s2_end": quarter * 2,
                "s3_start": quarter * 2 + 1,
                "s3_end": quarter * 3,
                "s4_start": quarter * 3 + 1,
                "format_instructions": self.lyricist_parser.get_format_instructions()
            }

            lyricist_output = self.lyricist_chain.invoke(lyricist_input)
            lyricist_duration = time.time() - lyricist_start

            print(f"✓ Lyricist complete in {lyricist_duration:.2f}s\n")
            print("=== LYRICIST OUTPUT (Bars) ===")
            print(json.dumps(lyricist_output.model_dump(), indent=2))
            print("==============================\n")

            # Step 2: Validate Lyricist output
            print("🔍 Validating Lyricist output...")
            validate_lyricist_output(lyricist_output, bars)
            print()

            # Step 3: Build TTS prompt
            print("🎵 Building TTS prompt...")
            grid_builder_start = time.time()

            grid_builder_output = build_grid_from_lyrics(
                lyricist_output, self.bpm, self.seconds
            )
            grid_builder_duration = time.time() - grid_builder_start

            print(f"✓ TTS prompt built in {grid_builder_duration:.4f}s\n")

            # Step 4: Display final TTS prompt
            print("=== FINAL TTS PROMPT ===")
            print(grid_builder_output.tts_prompt)
            print("========================\n")

            # Step 5: Generate music using ElevenLabs (or mock)
            mock_mode = os.environ.get("MOCK_ELEVENLABS", "").lower() in ("true", "1", "yes")
            mock_response_path = os.environ.get("MOCK_RESPONSE_PATH", "")

            music_file_path = None
            try:
                if mock_mode and mock_response_path:
                    # Mock mode: simulate API delay and use existing audio file
                    delay = random.uniform(5, 15)
                    print(f"🎼 [MOCK MODE] Simulating ElevenLabs API call...")
                    print(f"   Using mock response: {mock_response_path}")
                    print(f"   Simulating {delay:.1f}s API delay...")
                    time.sleep(delay)
                    music_file_path = mock_response_path
                    print(f"✓ [MOCK] Audio ready: {music_file_path}\n")
                else:
                    # Real API call
                    print("🎼 Step 3: Generating music with ElevenLabs...")
                    input("Press Enter to call ElevenLabs API (or Ctrl+C to cancel)...")
                    music_file_path = generate_music(
                        tts_prompt=grid_builder_output.tts_prompt,
                        seconds=self.seconds,
                        api_key=self.elevenlabs_api_key
                    )
                    print(f"✓ Music file saved: {music_file_path}\n")

                # Load the AI response audio and schedule overlay at next bar
                from audio_player import load_audio_file, SAMPLE_RATE
                response_audio = load_audio_file(music_file_path)

                # Calculate sample position for next bar boundary
                wait_ms = self.mixer.beat_tracker.ms_until_next_bar()
                insert_sample = self.mixer.get_current_sample() + int(wait_ms * SAMPLE_RATE / 1000)

                print(f"Scheduling AI response at next bar ({wait_ms:.0f}ms)...")
                self.mixer.schedule_overlay(response_audio, insert_sample)

                # Wait for overlay to finish playing
                overlay_duration_ms = len(response_audio) / SAMPLE_RATE * 1000
                total_wait_ms = wait_ms + overlay_duration_ms
                print(f"Playing AI response ({overlay_duration_ms:.0f}ms duration)...")
                time.sleep(total_wait_ms / 1000)

            except Exception as e:
                print(f"⚠️  Music generation failed: {e}")
                print("   Continuing without audio output...\n")

            # Calculate total agent timing
            total_agent_time = lyricist_duration + grid_builder_duration

            # Print timing summary
            print("\n" + "=" * 70)
            print("⏱️  AGENT TIMING SUMMARY")
            print("=" * 70)
            print(f"Lyricist:      {lyricist_duration:>8.2f}s  ({lyricist_duration/total_agent_time*100:>5.1f}%)")
            print(f"Grid Builder:  {grid_builder_duration:>8.2f}s  ({grid_builder_duration/total_agent_time*100:>5.1f}%)")
            print("─" * 70)
            print(f"Total:         {total_agent_time:>8.2f}s  (100.0%)")
            print("=" * 70 + "\n")

            print("✓ Pipeline complete!")

            return {
                "lyricist_output": lyricist_output,
                "grid_builder_output": grid_builder_output,
                "music_file_path": music_file_path,
                "timing": {
                    "lyricist_seconds": round(lyricist_duration, 2),
                    "grid_builder_seconds": round(grid_builder_duration, 2),
                    "total_seconds": round(total_agent_time, 2)
                }
            }

        finally:
            # Ensure mixer is stopped on exit (normal or exception)
            self.mixer.stop()


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

=== LYRICIST OUTPUT (Lyrics) ===
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

=== GRID BUILDER OUTPUT (Performance Grid) ===
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
