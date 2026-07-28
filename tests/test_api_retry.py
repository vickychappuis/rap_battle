"""Retry behaviour: the pipeline must resume, never redo or double-run.

Finding #1 (a retry re-ran every stage from transcription) and finding #18
(two rapid retries spawning two threads on one session).
"""

import threading

from conftest import (
    TEST_BARS,
    start_session,
    upload_turn,
    wait_for_step,
)


def test_retry_after_music_failure_does_not_rerun_the_lyricist(
    client, recording, fake_externals
):
    """Resumption is generic: a stage that succeeded is never re-run.

    The failure here is *after* the lyricist, so the retry must reuse both the
    transcription and the already-written bars and only redo the audio call.
    """
    sid = start_session(client)["session_id"]

    fake_externals.music_error = RuntimeError("elevenlabs 500")
    upload_turn(client, sid, recording)
    assert wait_for_step(client, sid, {"error"})["step"] == "error"

    assert client.post(f"/api/session/{sid}/retry").status_code == 200
    status = wait_for_step(client, sid, {"awaiting_user", "complete", "error"})

    assert status["step"] == "awaiting_user", status["error"]
    assert len(fake_externals.transcribe_calls) == 1
    assert len(fake_externals.lyricist_calls) == 1, (
        "the retry re-ran the lyricist even though it had already succeeded"
    )
    assert len(fake_externals.music_calls) == 2  # the failed one, then the retry
    assert [t["player"] for t in status["turn_history"]] == ["user", "ai"]


def test_retry_after_transcription_failure_retranscribes(
    client, recording, fake_externals
):
    """The flip side: a stage that did NOT succeed must still be re-run."""
    sid = start_session(client)["session_id"]

    fake_externals.transcribe_error = RuntimeError("stt down")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    assert client.post(f"/api/session/{sid}/retry").status_code == 200
    status = wait_for_step(client, sid, {"awaiting_user", "complete", "error"})

    assert status["step"] == "awaiting_user", status["error"]
    assert len(fake_externals.transcribe_calls) == 2
    assert [t["player"] for t in status["turn_history"]] == ["user", "ai"]


def test_retry_resets_the_error_and_keeps_turn_numbering(
    client, recording, fake_externals
):
    """A recovered turn leaves the session exactly as a clean run would."""
    sid = start_session(client)["session_id"]

    fake_externals.lyricist_error = RuntimeError("lyricist unavailable")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})
    client.post(f"/api/session/{sid}/retry")
    status = wait_for_step(client, sid, {"awaiting_user"})

    assert status["error"] is None
    assert status["retry_count"] == 0, "retry budget not reset after success"
    assert status["current_turn"] == 3
    assert [(t["turn_number"], t["player"]) for t in status["turn_history"]] == [
        (1, "user"),
        (2, "ai"),
    ]

    # And the battle can still be finished normally.
    assert upload_turn(client, sid, recording).status_code == 200
    final = wait_for_step(client, sid, {"complete"})
    assert final["winner"] in ("user", "ai", "draw")
    assert len(fake_externals.transcribe_calls) == 2


def test_retry_works_after_the_recording_was_already_consumed(
    client, recording, fake_externals
):
    """Once transcribed, the temp recording is gone - retry must not need it."""
    from api.services.pipeline import sessions

    sid = start_session(client)["session_id"]
    fake_externals.lyricist_error = RuntimeError("lyricist unavailable")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    assert sessions[sid].audio_path is None, (
        "the recording should be released as soon as it has been transcribed"
    )

    resp = client.post(f"/api/session/{sid}/retry")
    assert resp.json()["status"] == "retrying", (
        "retry asked for a re-record even though the transcript was in hand"
    )
    assert wait_for_step(client, sid, {"awaiting_user"})["step"] == "awaiting_user"


def test_retry_needs_a_rerecord_when_transcription_never_succeeded(
    client, recording, fake_externals, monkeypatch
):
    """Without a transcript and without audio there is nothing to resume."""
    from api.services.pipeline import sessions

    sid = start_session(client)["session_id"]
    fake_externals.transcribe_error = RuntimeError("stt down")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    # Simulate the temp file disappearing (tmp reaper, container restart).
    session = sessions[sid]
    from pathlib import Path

    Path(session.audio_path).unlink(missing_ok=True)

    resp = client.post(f"/api/session/{sid}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "need_rerecord"
    assert client.get(f"/api/session/{sid}/status").json()["step"] == "awaiting_user"


def test_retry_is_rejected_when_not_in_error(client, recording, fake_externals):
    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"awaiting_user"})

    resp = client.post(f"/api/session/{sid}/retry")
    assert resp.status_code == 400


def test_retry_budget_is_capped_at_two_failures(client, recording, fake_externals):
    sid = start_session(client)["session_id"]

    fake_externals.lyricist_error = RuntimeError("down")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    fake_externals.lyricist_error = RuntimeError("still down")
    assert client.post(f"/api/session/{sid}/retry").status_code == 200
    status = wait_for_step(client, sid, {"error"})
    assert status["retry_count"] == 2
    assert "Failed after 2 attempts" in status["error"]

    assert client.post(f"/api/session/{sid}/retry").status_code == 400


# --- Finding #18: concurrent runs on one session ------------------------------


def test_second_retry_while_one_is_running_is_refused(
    client, recording, fake_externals, monkeypatch
):
    """A double-clicked /retry must not start a second pipeline thread."""
    import api.services.pipeline as pipeline_mod
    from core.models import LyricistOutput

    sid = start_session(client)["session_id"]
    fake_externals.lyricist_error = RuntimeError("lyricist unavailable")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    gate = threading.Event()
    invocations = []

    class _BlockingChain:
        def invoke(self, payload, *args, **kwargs):
            invocations.append(payload)
            assert gate.wait(10), "test gate never opened"
            return LyricistOutput(
                bars=[f"line {i + 1}" for i in range(TEST_BARS)],
                mood_arc="confident -> aggressive",
            )

    monkeypatch.setattr(
        pipeline_mod.pipeline_service, "_lyricist_chain", _BlockingChain()
    )

    first = client.post(f"/api/session/{sid}/retry")
    assert first.status_code == 200

    second = client.post(f"/api/session/{sid}/retry")
    assert second.status_code in (400, 409), (
        "a second retry was accepted while the first was still running"
    )

    gate.set()
    status = wait_for_step(client, sid, {"awaiting_user", "complete", "error"})
    assert status["step"] == "awaiting_user", status["error"]
    assert len(invocations) == 1, "two pipeline threads ran on the same session"
    assert [t["player"] for t in status["turn_history"]] == ["user", "ai"]


def test_run_slot_is_single_entry(client, recording, fake_externals):
    """The guard itself, without the route in the way."""
    from api.services.pipeline import SessionState, pipeline_service

    session = SessionState(
        session_id="guard", bpm=90, bars_per_turn=2, turns_per_player=1
    )
    assert session.try_acquire_run() is True
    assert session.try_acquire_run() is False, "the run slot was handed out twice"
    assert pipeline_service.resume_pipeline(session) is False
    session.release_run()
    assert session.try_acquire_run() is True


def test_upload_while_running_is_refused(client, recording, fake_externals):
    """The same guard covers a second upload racing the first."""
    sid = start_session(client)["session_id"]
    assert upload_turn(client, sid, recording).status_code == 200
    second = upload_turn(client, sid, recording)
    assert second.status_code in (400, 409)
    wait_for_step(client, sid, {"awaiting_user"})
    assert len(fake_externals.transcribe_calls) == 1
