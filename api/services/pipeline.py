"""Runs the rap battle pipeline in a background thread, updating session
state at each step so the frontend can poll for progress.

The pipeline is *resumable*: it is a list of stages, each of which knows how
to tell whether it already produced its result for the current recording. A
retry re-enters the same list and skips everything that already succeeded, so
no external call (and no billed API call) is ever made twice for one
recording, and the user's turn is committed to the history exactly once.
"""

import os
import json
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

from core.stt import transcribe_audio
from core.prompts import (
    TurnData as PromptTurnData,
    build_battle_context,
    build_opponent_persona_block,
    build_turn_instructions,
)
from core.models import LyricistOutput, GridBuilderOutput
from core.generation import (
    create_lyricist_agent,
    validate_lyricist_output,
    generate_music,
)
from core.grid_builder import build_grid_from_lyrics
from core.judge import judge_battle
from api.models.session import PipelineStep, TurnData

logger = logging.getLogger(__name__)


# How long an idle session (and the mp3s it generated) is kept before the
# next session creation sweeps it away. Sessions live in memory only, so
# without this the process grows for its whole lifetime.
# How many times a single turn may be retried before the player has to start
# over. The frontend mirrors this as MAX_TURN_RETRIES in hooks/useSession.ts to
# decide whether the mic offers "Retry" or "Start Over" — if the two ever
# disagree, the UI stops offering the only working recovery path, so keep them
# in step.
MAX_TURN_RETRIES = 2

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 3600))
GENERATED_AUDIO_TTL_SECONDS = int(
    os.environ.get("GENERATED_AUDIO_TTL_SECONDS", SESSION_TTL_SECONDS)
)

GENERATED_AUDIO_DIR = Path(__file__).parent.parent / "static" / "generated"


def _content_logging_enabled() -> bool:
    """Whether full transcriptions / lyrics may be printed.

    Off by default: AGENTS.md forbids logging raw user content. Set
    DEBUG_LOG_CONTENT=true locally when debugging prompt quality.
    """
    return os.environ.get("DEBUG_LOG_CONTENT", "").lower() in ("true", "1", "yes")


def _log_content(title: str, body: str) -> None:
    """Log sensitive content only when the debug flag is on."""
    if not _content_logging_enabled():
        return
    logger.info("=== %s ===\n%s", title, body)


@dataclass
class SessionState:
    """In-memory state for a battle session."""
    session_id: str
    bpm: int
    bars_per_turn: int
    turns_per_player: int
    opponent_name: str = "the challenger"
    # Client-supplied character sheet for the AI MC (name / age / claims /
    # reality / extra_info), already validated and sanitised by the route's
    # `OpponentPersona` model. None means "no persona for this battle".
    opponent_persona: Optional[dict] = None

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

    # Stage bookkeeping for the current recording. These make the pipeline
    # resumable: a retry skips whatever is already recorded as done.
    user_turn_committed: bool = False
    ai_turn_committed: bool = False

    # Reclamation + concurrency
    last_activity: float = field(default_factory=time.time)
    running: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

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

    def touch(self) -> None:
        """Mark the session as recently used so the TTL sweep spares it."""
        self.last_activity = time.time()

    def try_acquire_run(self) -> bool:
        """Claim the single pipeline slot for this session.

        Returns False if a pipeline thread is already running, which is what
        stops a double-clicked /retry from spawning two threads that mutate
        the same session.
        """
        with self._lock:
            if self.running:
                return False
            self.running = True
            return True

    def release_run(self) -> None:
        with self._lock:
            self.running = False

    def clear_current_turn_data(self):
        """Clear data from the current turn for a fresh start.

        Called when a NEW recording arrives - it throws away the resumable
        stage results of the previous recording. A retry must never call it.
        """
        self.transcription = None
        self.lyrics = None
        self.ai_audio_url = None
        self.error = None
        self.timing = None
        self.lyricist_output = None
        self.grid_builder_output = None
        self.user_turn_committed = False
        self.ai_turn_committed = False


@dataclass
class _Stage:
    """One resumable unit of pipeline work.

    `is_done` is checked before running: it reports whether this stage already
    produced its result for the recording currently being processed.
    """
    name: str
    step: PipelineStep
    is_done: Callable[[SessionState], bool]
    run: Callable[[SessionState], None]
    timing_key: Optional[str] = None
    timing_precision: int = 2


# Global session storage (in-memory for POC)
sessions: Dict[str, SessionState] = {}


def cleanup_expired(now: Optional[float] = None) -> dict:
    """Drop stale sessions and generated mp3s (TTL-based, swept on demand).

    Called when a new session is created - no scheduler, no new dependency.
    Returns a small summary, mostly so tests can assert on it.
    """
    now = now if now is not None else time.time()

    expired = [
        sid
        for sid, s in list(sessions.items())  # snapshot: other requests may add
        if not s.running and now - s.last_activity > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        session = sessions.pop(sid, None)
        if session is not None and session.audio_path:
            Path(session.audio_path).unlink(missing_ok=True)

    removed_files = 0
    if GENERATED_AUDIO_DIR.exists():
        for path in GENERATED_AUDIO_DIR.glob("*.mp3"):
            try:
                if now - path.stat().st_mtime > GENERATED_AUDIO_TTL_SECONDS:
                    path.unlink()
                    removed_files += 1
            except OSError:
                pass

    if expired or removed_files:
        logger.info(
            "Cleanup: removed %d expired session(s) and %d generated file(s)",
            len(expired),
            removed_files,
        )
    return {"sessions_removed": len(expired), "files_removed": removed_files}


class PipelineService:
    """Service to run the rap battle pipeline in a background thread."""

    def __init__(self):
        # The LLM client is built lazily (see `lyricist_chain`) so importing
        # the app never requires an API key - /health must answer even when
        # the environment is misconfigured.
        self._lyricist_chain = None
        self._lyricist_parser = None
        self._llm_lock = threading.Lock()

    # --- Lazily built external clients ------------------------------------

    @property
    def openai_api_key(self) -> Optional[str]:
        return os.environ.get("OPENAI_API_KEY")

    @property
    def elevenlabs_api_key(self) -> Optional[str]:
        return os.environ.get("ELEVENLABS_API_KEY")

    def _ensure_lyricist(self) -> None:
        """Build the lyricist chain on first use, with a readable failure."""
        if self._lyricist_chain is not None and self._lyricist_parser is not None:
            return
        with self._llm_lock:
            if self._lyricist_chain is not None and self._lyricist_parser is not None:
                return
            if not self.openai_api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set - the lyricist cannot run. "
                    "Set it in your environment or .env file (see .env.example)."
                )
            # Grid building is pure Python; only the lyricist needs an LLM.
            chain, parser = create_lyricist_agent()
            self._lyricist_chain = chain
            self._lyricist_parser = parser

    @property
    def lyricist_chain(self):
        self._ensure_lyricist()
        return self._lyricist_chain

    @lyricist_chain.setter
    def lyricist_chain(self, value):
        self._lyricist_chain = value

    @property
    def lyricist_parser(self):
        self._ensure_lyricist()
        return self._lyricist_parser

    @lyricist_parser.setter
    def lyricist_parser(self, value):
        self._lyricist_parser = value

    # --- Entry points ------------------------------------------------------

    def start_pipeline(self, session: SessionState, audio_path: str) -> bool:
        """Start a fresh turn from a newly uploaded recording.

        Returns False if a pipeline run is already in flight for this session.
        """
        if not session.try_acquire_run():
            return False
        session.clear_current_turn_data()
        session.audio_path = audio_path
        # Set synchronously so the next request sees a busy session even
        # before the background thread gets scheduled.
        session.step = PipelineStep.RECORDING
        session.touch()
        self._launch(session)
        return True

    def resume_pipeline(self, session: SessionState) -> bool:
        """Re-enter the pipeline after an error, keeping finished stages.

        Returns False if a pipeline run is already in flight for this session.
        """
        if not session.try_acquire_run():
            return False
        session.touch()
        # Move off ERROR synchronously so a poll right after /retry sees the
        # stage we are resuming into rather than the stale error state.
        for stage in self._build_stages():
            if not stage.is_done(session):
                session.step = stage.step
                break
        self._launch(session)
        return True

    def _launch(self, session: SessionState) -> None:
        thread = threading.Thread(target=self._run_pipeline, args=(session,))
        thread.daemon = True
        thread.start()

    # --- Stages ------------------------------------------------------------

    def _build_stages(self) -> List[_Stage]:
        return [
            _Stage(
                name="Transcription",
                step=PipelineStep.TRANSCRIBING,
                is_done=lambda s: s.transcription is not None,
                run=self._stage_transcribe,
                timing_key="transcription_seconds",
            ),
            _Stage(
                name="User turn",
                step=PipelineStep.TRANSCRIBING,
                is_done=lambda s: s.user_turn_committed,
                run=self._stage_commit_user_turn,
            ),
            _Stage(
                name="Lyricist",
                step=PipelineStep.GENERATING_LYRICS,
                is_done=lambda s: s.lyricist_output is not None,
                run=self._stage_lyricist,
                timing_key="lyricist_seconds",
            ),
            _Stage(
                name="Grid builder",
                step=PipelineStep.GENERATING_LYRICS,
                is_done=lambda s: s.grid_builder_output is not None,
                run=self._stage_grid_builder,
                timing_key="grid_builder_seconds",
                timing_precision=4,
            ),
            _Stage(
                name="Audio generation",
                step=PipelineStep.GENERATING_AUDIO,
                is_done=lambda s: s.ai_audio_url is not None,
                run=self._stage_generate_audio,
                timing_key="audio_generation_seconds",
            ),
            _Stage(
                name="AI turn",
                step=PipelineStep.GENERATING_AUDIO,
                is_done=lambda s: s.ai_turn_committed,
                run=self._stage_commit_ai_turn,
            ),
        ]

    def _run_pipeline(self, session: SessionState) -> None:
        """Run (or resume) the pipeline (called in background thread)."""
        final_step = PipelineStep.ERROR
        try:
            if session.timing is None:
                session.timing = {}

            for stage in self._build_stages():
                if stage.is_done(session):
                    logger.info("%s: already done for this recording, skipping", stage.name)
                    continue
                session.step = stage.step
                started = time.time()
                stage.run(session)
                elapsed = time.time() - started
                if stage.timing_key:
                    session.timing[stage.timing_key] = round(
                        elapsed, stage.timing_precision
                    )
                    logger.info("%s completed in %.2fs", stage.name, elapsed)

            final_step = self._finish_turn(session)

        except Exception as e:
            session.retry_count += 1
            final_step = PipelineStep.ERROR
            if session.retry_count >= MAX_TURN_RETRIES:
                session.error = f"Failed after {MAX_TURN_RETRIES} attempts: {str(e)}"
                # Out of retries: nothing left to resume, drop the recording.
                self._cleanup_audio(session)
            else:
                session.error = f"Attempt {session.retry_count} failed: {str(e)}. You can retry."
                # Completed stages stay on the session so a retry can resume.
        finally:
            session.touch()
            # Free the run slot *before* advertising a terminal step, so a
            # client that reacts to `awaiting_user`/`error` immediately can
            # never be turned away by a slot this run has not released yet.
            session.release_run()
            session.step = final_step

    def _stage_transcribe(self, session: SessionState) -> None:
        session.transcription = transcribe_audio(session.audio_path)
        _log_content("OPPONENT BARS (STT Transcription)", session.transcription)

    def _stage_commit_user_turn(self, session: SessionState) -> None:
        """Append the user's verse to the history exactly once."""
        session.turn_history.append(
            TurnData(
                turn_number=session.current_turn,
                player="user",
                transcription=session.transcription,
            )
        )
        session.current_turn += 1
        session.user_turn_committed = True
        # The recording has been turned into text; it is no longer needed,
        # and a retry resumes from the transcript instead of the audio.
        self._cleanup_audio(session)

    def _stage_lyricist(self, session: SessionState) -> None:
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
        # Scales with TURNS_PER_PLAYER: opening / middle / final-round text.
        turn_instructions = build_turn_instructions(
            session.ai_turn_number, session.turns_per_player
        )

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
            "opponent_persona": build_opponent_persona_block(session.opponent_persona),
            "format_instructions": self.lyricist_parser.get_format_instructions()
        }

        output = self.lyricist_chain.invoke(lyricist_input)
        validate_lyricist_output(output, session.bars_per_turn)
        session.lyricist_output = output

        _log_content(
            "LYRICIST OUTPUT (Bars)",
            json.dumps(session.lyricist_output.model_dump(), indent=2),
        )

    def _stage_grid_builder(self, session: SessionState) -> None:
        """Build the TTS prompt (pure Python - instant)."""
        session.grid_builder_output = build_grid_from_lyrics(
            session.lyricist_output, session.bpm, session.seconds
        )
        session.lyrics = session.grid_builder_output.plain_take
        _log_content("FINAL TTS PROMPT", session.grid_builder_output.tts_prompt)

    def _stage_generate_audio(self, session: SessionState) -> None:
        GENERATED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        # Generate unique filename for this turn
        output_filename = f"{session.session_id}_turn{session.current_turn}.mp3"
        output_path = GENERATED_AUDIO_DIR / output_filename

        mock_mode = os.environ.get("MOCK_ELEVENLABS", "").lower() in ("true", "1", "yes")
        if mock_mode:
            # Fail loudly: silently falling through to the real API here would
            # bill a call the operator explicitly asked us not to make.
            mock_response_path = os.environ.get("MOCK_RESPONSE_PATH", "")
            if not mock_response_path:
                raise RuntimeError(
                    "MOCK_ELEVENLABS is enabled but MOCK_RESPONSE_PATH is not set. "
                    "Point it at an existing mp3 to use as the AI response."
                )
            if not Path(mock_response_path).is_file():
                raise RuntimeError(
                    f"MOCK_RESPONSE_PATH does not exist: {mock_response_path}"
                )
            shutil.copy(mock_response_path, output_path)
        else:
            # Write straight to the per-turn destination: the legacy default
            # path is a shared, second-resolution filename that concurrent
            # battles collide on.
            generate_music(
                tts_prompt=session.grid_builder_output.tts_prompt,
                seconds=session.seconds,
                api_key=self.elevenlabs_api_key,
                output_path=output_path,
            )

        session.ai_audio_url = f"/static/generated/{output_filename}"

    def _stage_commit_ai_turn(self, session: SessionState) -> None:
        """Append the AI's verse to the history exactly once."""
        session.turn_history.append(
            TurnData(
                turn_number=session.current_turn,
                player="ai",
                lyrics=session.lyrics,
                audio_url=session.ai_audio_url,
                timing=dict(session.timing or {}),
            )
        )
        session.current_turn += 1
        session.ai_turn_committed = True

    def _finish_turn(self, session: SessionState) -> PipelineStep:
        """Wrap up a completed turn: timings, cleanup, next step.

        Returns the terminal step; the caller assigns it once the session's
        run slot has been released.
        """
        timing = session.timing or {}
        total_duration = sum(
            timing.get(key, 0.0)
            for key in (
                "transcription_seconds",
                "lyricist_seconds",
                "grid_builder_seconds",
                "audio_generation_seconds",
            )
        )
        timing["total_seconds"] = round(total_duration, 2)
        if session.turn_history and session.turn_history[-1].player == "ai":
            session.turn_history[-1].timing = dict(timing)

        self._print_timing_summary(session, timing, total_duration)

        # Reset retry count on success
        session.retry_count = 0
        self._cleanup_audio(session)

        # Determine next state
        if session.current_turn > session.total_turns:
            session.step = PipelineStep.JUDGING
            self._judge_battle(session)
            return PipelineStep.COMPLETE
        return PipelineStep.AWAITING_USER

    def _print_timing_summary(self, session: SessionState, timing: dict, total: float) -> None:
        def pct(value: float) -> float:
            return (value / total * 100) if total else 0.0

        lines = [f"TIMING SUMMARY (Turn {session.current_turn - 1})"]
        for label, key in (
            ("Transcription:    ", "transcription_seconds"),
            ("Lyricist:         ", "lyricist_seconds"),
            ("Grid Builder:     ", "grid_builder_seconds"),
            ("Audio Generation: ", "audio_generation_seconds"),
        ):
            value = timing.get(key, 0.0)
            lines.append(f"{label} {value:>6.2f}s  ({pct(value):>5.1f}%)")
        lines.append(f"Total:             {total:>6.2f}s  (100.0%)")
        logger.info("\n".join(lines))

    def _judge_battle(self, session: SessionState) -> None:
        """Have the core judge score the battle and store the verdict."""
        session.winner, session.judge_reason = judge_battle(
            session.turn_history,
            session.opponent_name,
            session.opponent_persona,
            api_key=self.openai_api_key,
        )
        _log_content("JUDGE REASON", session.judge_reason or "")

    def _cleanup_audio(self, session: SessionState) -> None:
        """Clean up temp audio file."""
        if session.audio_path and Path(session.audio_path).exists():
            try:
                Path(session.audio_path).unlink()
            except Exception:
                pass
        session.audio_path = None


# Global service instance (cheap to build: no network clients yet)
pipeline_service = PipelineService()
