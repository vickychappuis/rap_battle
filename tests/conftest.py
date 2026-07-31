"""Shared fixtures for the backend test suite.

The battle pipeline talks to three external services: OpenAI transcription,
an OpenAI-backed lyricist chain, and ElevenLabs music generation. Every test
here stubs those three boundaries and nothing else, so the FastAPI routes,
the background pipeline thread and the real domain logic all run for real.
"""

import os
import time
from pathlib import Path

# The API builds its LLM client lazily, so importing `api.main` needs no key.
# The dummy values still stand in for the credentials the stubbed external
# services would otherwise be handed.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "el-test-dummy")

import pytest
from fastapi.testclient import TestClient

# Keep battles short so the suite stays fast: 2 bars at 90bpm is ~5s of audio.
TEST_BPM = 90
TEST_BARS = 2
TEST_TURNS_PER_PLAYER = 2

TERMINAL_STEPS = {"awaiting_user", "complete", "error"}

# The stubs answer instantly, which would let a whole turn finish between two
# HTTP calls in the same test and make "is a second request rejected while the
# pipeline runs?" assertions racy. One short pause at the first stage keeps the
# pipeline observably in flight without slowing the suite down.
STUB_LATENCY_SECONDS = 0.1


def drain_pipelines(timeout=10.0):
    """Block until no session has a pipeline thread in flight.

    Pipeline threads are daemons started per turn. A test that deliberately
    leaves one running (e.g. asserting a second upload is rejected mid-turn)
    would otherwise let it run on into the *next* test, where it picks up the
    next test's stubs and consumes their queued errors.
    """
    from api.services.pipeline import sessions

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(s.running for s in list(sessions.values())):
            return True
        time.sleep(0.01)
    return False


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Clear the in-memory session store and rate limiter between tests.

    Both are module-level globals; without this the 4-per-hour limit trips
    partway through the suite and sessions leak across tests.
    """
    from api.routes import session as session_route
    from api.services.pipeline import sessions

    sessions.clear()
    session_route._session_timestamps.clear()
    yield
    drain_pipelines()  # backstop; the `client` fixture drains first
    sessions.clear()
    session_route._session_timestamps.clear()


@pytest.fixture
def turns_per_player(request):
    """Rounds per player for the session under test.

    Defaults to the short 2-round battle. Override it for a single test with
    `@pytest.mark.parametrize("turns_per_player", [3], indirect=True)`.
    """
    return getattr(request, "param", TEST_TURNS_PER_PLAYER)


@pytest.fixture(autouse=True)
def _short_battle(monkeypatch, turns_per_player):
    """Shrink the battle so recordings and generated audio stay small.

    The BPM comes from the track catalog, so the tests pin it by pinning the
    catalog to a single known track.
    """
    from api import tracks as tracks_mod
    from api.routes import session as session_route

    monkeypatch.setattr(
        tracks_mod, "TRACKS", [tracks_mod.Track("base_90bpm.mp3", TEST_BPM)]
    )
    monkeypatch.setattr(session_route, "BARS_PER_TURN", TEST_BARS)
    monkeypatch.setattr(session_route, "TURNS_PER_PLAYER", turns_per_player)


class FakeExternals:
    """Records every call to a stubbed external service.

    Tests assert on these counters to catch duplicated work (e.g. a retry
    re-transcribing audio that was already transcribed).
    """

    def __init__(self):
        self.transcribe_calls = []
        self.lyricist_calls = []
        self.music_calls = []
        self.judge_calls = []
        # Set to an exception instance to make the next call to that service
        # raise; it is cleared once it has fired.
        self.transcribe_error = None
        self.lyricist_error = None
        self.music_error = None

    def _maybe_raise(self, attr):
        err = getattr(self, attr)
        if err is not None:
            setattr(self, attr, None)
            raise err


@pytest.fixture
def fake_externals(monkeypatch):
    """Stub transcription, the lyricist chain, ElevenLabs and the judge."""
    import api.services.pipeline as pipeline_mod
    from core.models import LyricistOutput

    fake = FakeExternals()

    def fake_transcribe(audio_path, *args, **kwargs):
        fake.transcribe_calls.append(audio_path)
        time.sleep(STUB_LATENCY_SECONDS)
        fake._maybe_raise("transcribe_error")
        return f"your bars are weak, take {len(fake.transcribe_calls)}"

    def fake_lyricist_invoke(payload):
        fake.lyricist_calls.append(payload)
        fake._maybe_raise("lyricist_error")
        return LyricistOutput(
            bars=[f"line {i + 1}" for i in range(TEST_BARS)],
            mood_arc="confident -> aggressive",
        )

    def fake_generate_music(tts_prompt, seconds, api_key, output_path, **kwargs):
        fake.music_calls.append(
            {"prompt": tts_prompt, "seconds": seconds, "output_path": output_path}
        )
        fake._maybe_raise("music_error")
        # Mirrors the real helper: write to the caller's destination.
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"ID3fake-mp3-bytes")
        return str(out)

    class _FakeJudgeClient:
        def __init__(self, *args, **kwargs):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            fake.judge_calls.append(kwargs)
            content = '{"winner": "user", "reason": "you had the harder bars"}'
            message = type("M", (), {"content": content})()
            choice = type("C", (), {"message": message})()
            return type("R", (), {"choices": [choice]})()

    # The lyricist chain is a frozen pydantic RunnableSequence, so swap the
    # whole object rather than patching a method on it. We fill the service's
    # lazy cache directly: touching the public `lyricist_chain` property would
    # build a real LangChain client just to read the value back.
    class _FakeChain:
        def invoke(self, payload, *args, **kwargs):
            return fake_lyricist_invoke(payload)

    class _FakeParser:
        def get_format_instructions(self):
            return "(format instructions)"

    monkeypatch.setattr(pipeline_mod, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(pipeline_mod, "generate_music", fake_generate_music)
    monkeypatch.setattr(
        pipeline_mod.pipeline_service, "_lyricist_chain", _FakeChain()
    )
    monkeypatch.setattr(
        pipeline_mod.pipeline_service, "_lyricist_parser", _FakeParser()
    )
    monkeypatch.setattr("openai.OpenAI", _FakeJudgeClient)

    return fake


@pytest.fixture
def client(fake_externals):
    """A TestClient with all external services stubbed."""
    from api.main import app

    with TestClient(app) as c:
        yield c
        # Let any still-running turn finish while the stubs are still in
        # place, so it can never leak into the next test (or hit a real API).
        assert drain_pipelines(), "a pipeline thread outlived its test"


@pytest.fixture
def recording():
    """A tiny fake WebM upload payload."""
    return ("recording.webm", b"\x1a\x45\xdf\xa3fake-webm-audio", "audio/webm")


def wait_for_step(client, session_id, steps=TERMINAL_STEPS, timeout=10.0):
    """Poll /status until the pipeline reaches one of `steps`.

    The pipeline runs on a background thread, so tests must poll exactly as
    the real frontend does rather than reaching into session state.
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/session/{session_id}/status").json()
        if last["step"] in steps:
            return last
        time.sleep(0.02)
    raise AssertionError(
        f"pipeline stuck at step={last and last['step']!r} after {timeout}s"
    )


def start_session(client, opponent_name="Max Gorilla"):
    resp = client.post("/api/session", json={"opponent_name": opponent_name})
    assert resp.status_code == 200, resp.text
    return resp.json()


def upload_turn(client, session_id, recording):
    return client.post(
        f"/api/session/{session_id}/recording",
        files={"audio": recording},
    )
