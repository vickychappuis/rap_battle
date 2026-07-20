"""Runs the rap battle pipeline in a background thread, updating session
state at each step so the frontend can poll for progress."""

import os
import json
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

from stt import transcribe_audio
from prompts import (
    TURN_INSTRUCTIONS,
    TurnData as PromptTurnData,
    build_battle_context,
)
from models import LyricistOutput, GridBuilderOutput
from generation import (
    create_lyricist_agent,
    validate_lyricist_output,
    generate_music,
)
from grid_builder_python import build_grid_from_lyrics
from api.models.session import PipelineStep, TurnData


@dataclass
class SessionState:
    """In-memory state for a battle session."""
    session_id: str
    bpm: int
    bars_per_turn: int
    turns_per_player: int
    opponent_name: str = "the challenger"

    # Derived values (calculated in __post_init__)
    grid_beats: int = field(init=False)
    seconds: float = field(init=False)

    # State
    step: PipelineStep = PipelineStep.IDLE
    current_turn: int = 1
    turn_history: List[TurnData] = field(default_factory=list)
    retry_count: int = 0

    # Current turn data (cleared each turn)
    transcription: Optional[str] = None
    lyrics: Optional[str] = None
    ai_audio_url: Optional[str] = None
    error: Optional[str] = None
    timing: Optional[dict] = None

    # Judge results
    winner: Optional[str] = None
    judge_reason: Optional[str] = None

    # Internal state
    audio_path: Optional[str] = None
    lyricist_output: Optional[LyricistOutput] = None
    grid_builder_output: Optional[GridBuilderOutput] = None

    def __post_init__(self):
        self.grid_beats = self.bars_per_turn * 4
        self.seconds = self.grid_beats * (60 / self.bpm)

    @property
    def total_turns(self) -> int:
        """Total number of turns in the battle (user + AI turns)."""
        return self.turns_per_player * 2

    @property
    def is_final_turn(self) -> bool:
        """Check if this is the final turn of the battle."""
        return self.current_turn >= self.total_turns

    @property
    def ai_turn_number(self) -> int:
        """Which AI turn is this? (1-indexed)"""
        return (self.current_turn + 1) // 2

    def clear_current_turn_data(self):
        """Clear data from the current turn for a fresh start."""
        self.transcription = None
        self.lyrics = None
        self.ai_audio_url = None
        self.error = None
        self.timing = None
        self.lyricist_output = None
        self.grid_builder_output = None


# Global session storage (in-memory for POC)
sessions: Dict[str, SessionState] = {}


class PipelineService:
    """Service to run the rap battle pipeline in a background thread."""

    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")

        # Grid building is pure Python; only the lyricist needs an LLM.
        self.lyricist_chain, self.lyricist_parser = create_lyricist_agent()

    def start_pipeline(self, session: SessionState, audio_path: str) -> None:
        """Start the pipeline in a background thread."""
        session.audio_path = audio_path
        thread = threading.Thread(target=self._run_pipeline, args=(session,))
        thread.daemon = True
        thread.start()

    def _run_pipeline(self, session: SessionState) -> None:
        """Run the full pipeline (called in background thread)."""
        try:
            session.timing = {}
            pipeline_start = time.time()

            # Step 1: Transcribe audio
            session.step = PipelineStep.TRANSCRIBING
            transcribe_start = time.time()
            session.transcription = transcribe_audio(session.audio_path)
            transcribe_duration = time.time() - transcribe_start
            session.timing['transcription_seconds'] = round(transcribe_duration, 2)
            print(f"⏱️  Transcription completed in {transcribe_duration:.2f}s")

            print("\n=== OPPONENT BARS (STT Transcription) ===")
            print(session.transcription)
            print("==========================================\n")

            # Save user turn to history
            user_turn = TurnData(
                turn_number=session.current_turn,
                player="user",
                transcription=session.transcription
            )
            session.turn_history.append(user_turn)
            session.current_turn += 1

            # Step 2: Generate lyrics with battle context
            session.step = PipelineStep.GENERATING_LYRICS
            lyricist_start = time.time()

            # Convert TurnData (Pydantic) to PromptTurnData (dataclass) for build_battle_context
            prompt_history = [
                PromptTurnData(
                    turn_number=t.turn_number,
                    player=t.player,
                    transcription=t.transcription,
                    lyrics=t.lyrics
                )
                for t in session.turn_history[:-1]  # Exclude current user turn
            ]
            battle_context = build_battle_context(prompt_history)
            turn_instructions = TURN_INSTRUCTIONS.get(session.ai_turn_number, "Deliver your best bars.")

            quarter = max(1, session.bars_per_turn // 4)
            seconds_per_bar = 4 * (60.0 / session.bpm)
            syllable_budget = session.grid_beats * 2  # ~2 syllables per beat avg

            lyricist_input = {
                "opponent_bars": session.transcription,
                "bpm": session.bpm,
                "bars": session.bars_per_turn,
                "seconds": session.seconds,
                "seconds_per_bar": seconds_per_bar,
                "syllable_budget": syllable_budget,
                "s1_end": quarter,
                "s2_start": quarter + 1,
                "s2_end": quarter * 2,
                "s3_start": quarter * 2 + 1,
                "s3_end": quarter * 3,
                "s4_start": quarter * 3 + 1,
                "turn_number": session.current_turn,
                "total_turns": session.total_turns,
                "battle_context": battle_context,
                "turn_instructions": turn_instructions,
                "format_instructions": self.lyricist_parser.get_format_instructions()
            }

            session.lyricist_output = self.lyricist_chain.invoke(lyricist_input)
            validate_lyricist_output(session.lyricist_output, session.bars_per_turn)

            lyricist_duration = time.time() - lyricist_start
            session.timing['lyricist_seconds'] = round(lyricist_duration, 2)
            print(f"⏱️  Lyricist completed in {lyricist_duration:.2f}s")

            # Log Lyricist output
            print("\n=== LYRICIST OUTPUT (Bars) ===")
            print(json.dumps(session.lyricist_output.model_dump(), indent=2))
            print("==============================\n")

            # Build TTS prompt (Python - instant)
            grid_builder_start = time.time()
            session.grid_builder_output = build_grid_from_lyrics(
                session.lyricist_output, session.bpm, session.seconds
            )
            session.lyrics = session.grid_builder_output.plain_take

            grid_builder_duration = time.time() - grid_builder_start
            session.timing['grid_builder_seconds'] = round(grid_builder_duration, 4)
            print(f"⏱️  TTS prompt built in {grid_builder_duration:.4f}s")

            # Step 3: Generate audio
            session.step = PipelineStep.GENERATING_AUDIO
            audio_start = time.time()

            print("=== FINAL TTS PROMPT ===")
            print(session.grid_builder_output.tts_prompt)
            print("========================\n")

            # Ensure output directory exists
            output_dir = Path(__file__).parent.parent / "static" / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Check for mock mode
            mock_mode = os.environ.get("MOCK_ELEVENLABS", "").lower() in ("true", "1", "yes")
            mock_response_path = os.environ.get("MOCK_RESPONSE_PATH", "")

            # Generate unique filename for this turn
            output_filename = f"{session.session_id}_turn{session.current_turn}.mp3"
            output_path = output_dir / output_filename

            if mock_mode and mock_response_path:
                shutil.copy(mock_response_path, output_path)
            else:
                music_file_path = generate_music(
                    tts_prompt=session.grid_builder_output.tts_prompt,
                    seconds=session.seconds,
                    api_key=self.elevenlabs_api_key
                )
                shutil.move(music_file_path, output_path)

            session.ai_audio_url = f"/static/generated/{output_filename}"

            audio_duration = time.time() - audio_start
            session.timing['audio_generation_seconds'] = round(audio_duration, 2)
            print(f"⏱️  Audio generation completed in {audio_duration:.2f}s")

            # Calculate total timing
            total_duration = time.time() - pipeline_start
            session.timing['total_seconds'] = round(total_duration, 2)

            # Log timing summary
            print("\n" + "=" * 70)
            print(f"⏱️  TIMING SUMMARY (Turn {session.current_turn})")
            print("=" * 70)
            print(f"Transcription:     {session.timing['transcription_seconds']:>6.2f}s  ({session.timing['transcription_seconds']/total_duration*100:>5.1f}%)")
            print(f"Lyricist:          {session.timing['lyricist_seconds']:>6.2f}s  ({session.timing['lyricist_seconds']/total_duration*100:>5.1f}%)")
            print(f"Grid Builder:      {session.timing['grid_builder_seconds']:>6.2f}s  ({session.timing['grid_builder_seconds']/total_duration*100:>5.1f}%)")
            print(f"Audio Generation:  {session.timing['audio_generation_seconds']:>6.2f}s  ({session.timing['audio_generation_seconds']/total_duration*100:>5.1f}%)")
            print("─" * 70)
            print(f"Total:             {total_duration:>6.2f}s  (100.0%)")
            print("=" * 70 + "\n")

            # Save AI turn to history with timing
            ai_turn = TurnData(
                turn_number=session.current_turn,
                player="ai",
                lyrics=session.lyrics,
                audio_url=session.ai_audio_url,
                timing=session.timing.copy()
            )
            session.turn_history.append(ai_turn)
            session.current_turn += 1

            # Reset retry count on success
            session.retry_count = 0

            # Clean up audio file after successful processing
            self._cleanup_audio(session)

            # Determine next state
            if session.current_turn > session.total_turns:
                session.step = PipelineStep.JUDGING
                self._judge_battle(session)
                session.step = PipelineStep.COMPLETE
            else:
                session.step = PipelineStep.AWAITING_USER

        except Exception as e:
            session.retry_count += 1
            session.step = PipelineStep.ERROR
            if session.retry_count >= 2:
                session.error = f"Failed after 2 attempts: {str(e)}"
                # Clean up audio file after all retries exhausted
                self._cleanup_audio(session)
            else:
                session.error = f"Attempt {session.retry_count} failed: {str(e)}. You can retry."
                # Keep audio file for retry

    def _judge_battle(self, session: SessionState) -> None:
        """Use AI to judge the battle and pick a winner."""
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key)

        from prompts.judge_prompt import build_judge_system_prompt, build_judge_transcript

        opponent = session.opponent_name
        transcript = build_judge_transcript(session.turn_history, opponent)

        messages = [
            {"role": "system", "content": build_judge_system_prompt(opponent)},
            {"role": "user", "content": transcript},
        ]

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                result_text = response.choices[0].message.content or "{}"
                result = json.loads(result_text)
                winner = result.get("winner", "")
                if winner not in ("user", "ai"):
                    raise ValueError(f"Invalid winner value: '{winner}'")
                session.winner = winner
                session.judge_reason = result.get("reason", "")
                print(f"🏆 Judge decision: {session.winner} — {session.judge_reason}")
                return
            except Exception as e:
                print(f"⚠️  Judge attempt {attempt}/{max_attempts} failed: {e}")

        session.winner = "draw"
        session.judge_reason = "The judge couldn't decide — it's a draw!"

    def _cleanup_audio(self, session: SessionState) -> None:
        """Clean up temp audio file."""
        if session.audio_path and Path(session.audio_path).exists():
            try:
                Path(session.audio_path).unlink()
                session.audio_path = None
            except Exception:
                pass


# Global service instance
pipeline_service = PipelineService()
