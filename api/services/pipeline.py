"""
Pipeline service for async rap battle processing.

Wraps the existing orchestrator logic to run in a background thread,
updating session state at each step for frontend polling.
"""

import os
import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stt import transcribe_audio
from prompts import (
    LYRICIST_PROMPT_TEMPLATE,
    GRID_BUILDER_PROMPT_TEMPLATE,
    TURN_INSTRUCTIONS,
    TurnData as PromptTurnData,
    build_battle_context,
)
from main import (
    LyricistOutput,
    GridBuilderOutput,
    create_lyricist_agent,
    create_grid_builder_agent,
    validate_lyricist_output,
    generate_music,
)
from api.models.session import PipelineStep, TurnData


@dataclass
class SessionState:
    """In-memory state for a battle session."""
    session_id: str
    bpm: int
    bars_per_turn: int
    turns_per_player: int

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
        self.lyricist_output = None
        self.grid_builder_output = None


# Global session storage (in-memory for POC)
sessions: Dict[str, SessionState] = {}


class PipelineService:
    """Service to run the rap battle pipeline in a background thread."""

    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        # Create agents
        self.lyricist_chain, self.lyricist_parser = create_lyricist_agent(self.model)
        self.grid_builder_chain, self.grid_builder_parser = create_grid_builder_agent(self.model)

    def start_pipeline(self, session: SessionState, audio_path: str) -> None:
        """Start the pipeline in a background thread."""
        session.audio_path = audio_path
        thread = threading.Thread(target=self._run_pipeline, args=(session,))
        thread.daemon = True
        thread.start()

    def _run_pipeline(self, session: SessionState) -> None:
        """Run the full pipeline (called in background thread)."""
        try:
            # Step 1: Transcribe audio
            session.step = PipelineStep.TRANSCRIBING
            session.transcription = transcribe_audio(session.audio_path)

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

            lyricist_input = {
                "opponent_bars": session.transcription,
                "bpm": session.bpm,
                "bars": session.bars_per_turn,
                "seconds": session.seconds,
                "grid_beats": session.grid_beats,
                "grid_beats_minus_1": session.grid_beats - 1,
                "turn_number": session.current_turn,
                "total_turns": session.total_turns,
                "battle_context": battle_context,
                "turn_instructions": turn_instructions,
                "format_instructions": self.lyricist_parser.get_format_instructions()
            }

            session.lyricist_output = self.lyricist_chain.invoke(lyricist_input)
            validate_lyricist_output(session.lyricist_output, session.grid_beats)

            # Build grid
            grid_builder_input = {
                "lyricist_json": json.dumps(session.lyricist_output.model_dump(), indent=2),
                "bpm": session.bpm,
                "seconds": session.seconds,
                "format_instructions": self.grid_builder_parser.get_format_instructions()
            }

            session.grid_builder_output = self.grid_builder_chain.invoke(grid_builder_input)
            session.lyrics = session.grid_builder_output.plain_take

            # Step 3: Generate audio
            session.step = PipelineStep.GENERATING_AUDIO

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
                # Mock mode: copy existing file to output location
                import shutil
                shutil.copy(mock_response_path, output_path)
            else:
                # Real API call
                music_file_path = generate_music(
                    tts_prompt=session.grid_builder_output.tts_prompt,
                    seconds=session.seconds,
                    api_key=self.elevenlabs_api_key
                )
                # Move to static folder
                import shutil
                shutil.move(music_file_path, output_path)

            session.ai_audio_url = f"/static/generated/{output_filename}"

            # Save AI turn to history
            ai_turn = TurnData(
                turn_number=session.current_turn,
                player="ai",
                lyrics=session.lyrics,
                audio_url=session.ai_audio_url
            )
            session.turn_history.append(ai_turn)
            session.current_turn += 1

            # Reset retry count on success
            session.retry_count = 0

            # Clean up audio file after successful processing
            self._cleanup_audio(session)

            # Determine next state
            if session.current_turn > session.total_turns:
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
