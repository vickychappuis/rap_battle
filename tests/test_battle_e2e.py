"""End-to-end battle flows driven through the real HTTP API.

These exercise the full loop the browser performs: create a session, upload a
recording, poll for status, repeat for the second round, then read the verdict.
"""

import pytest
from conftest import (
    TEST_TURNS_PER_PLAYER,
    start_session,
    upload_turn,
    wait_for_step,
)

from api.services.pipeline import MAX_TURN_RETRIES


def test_full_two_round_battle(client, recording, fake_externals):
    """A complete battle: two user turns, two AI turns, then a verdict."""
    session = start_session(client)
    sid = session["session_id"]

    assert session["turns_per_player"] == TEST_TURNS_PER_PLAYER
    assert session["base_track_url"] == "/static/tracks/base_90bpm.mp3"
    assert session["record_duration"] > 0
    # The retry budget ships with the session so the UI never hardcodes it.
    assert session["max_turn_retries"] == MAX_TURN_RETRIES

    # --- Round 1 ---
    assert upload_turn(client, sid, recording).status_code == 200
    status = wait_for_step(client, sid, {"awaiting_user"})
    assert status["step"] == "awaiting_user"
    assert status["ai_audio_url"], "AI audio should be available after round 1"
    assert status["transcription"]
    assert status["lyrics"]

    # --- Round 2 ---
    assert upload_turn(client, sid, recording).status_code == 200
    status = wait_for_step(client, sid, {"complete"})

    # --- Verdict ---
    assert status["step"] == "complete"
    assert status["winner"] in ("user", "ai", "draw")
    assert status["judge_reason"]

    # Exactly one call per turn to each external service, no duplicates.
    assert len(fake_externals.transcribe_calls) == 2
    assert len(fake_externals.lyricist_calls) == 2
    assert len(fake_externals.music_calls) == 2
    assert len(fake_externals.judge_calls) == 1

    # History alternates user/ai for the full battle.
    history = [(t["turn_number"], t["player"]) for t in status["turn_history"]]
    assert history == [(1, "user"), (2, "ai"), (3, "user"), (4, "ai")]


def test_ai_gets_correct_turn_instructions(client, recording, fake_externals):
    """The lyricist must be told round 1 on its first verse, not the finale."""
    sid = start_session(client)["session_id"]

    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"awaiting_user"})

    first_call = fake_externals.lyricist_calls[0]
    assert "opening response" in first_call["turn_instructions"], (
        "first AI verse got the wrong turn instructions: "
        f"{first_call['turn_instructions']!r}"
    )

    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"complete"})

    second_call = fake_externals.lyricist_calls[1]
    assert "Final round" in second_call["turn_instructions"]


def test_lyricist_receives_battle_context(client, recording, fake_externals):
    """Round 2 must include round 1's exchange so the AI can call back to it."""
    sid = start_session(client)["session_id"]

    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"awaiting_user"})
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"complete"})

    assert fake_externals.lyricist_calls[0]["battle_context"] == (
        "This is the opening exchange."
    )
    later_context = fake_externals.lyricist_calls[1]["battle_context"]
    assert "Previous exchanges" in later_context
    assert "take 1" in later_context, "round 1 transcription missing from context"


def test_generated_audio_is_served_back(client, recording):
    """The URL handed to the frontend must actually resolve."""
    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"awaiting_user"})

    resp = client.get(status["ai_audio_url"])
    assert resp.status_code == 200
    assert resp.content, "generated audio served as empty body"


def test_status_404_for_unknown_session(client):
    assert client.get("/api/session/does-not-exist/status").status_code == 404


def test_upload_rejected_while_pipeline_running(client, recording, fake_externals):
    """A second upload mid-pipeline must not start a competing turn."""
    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)

    second = upload_turn(client, sid, recording)
    if second.status_code == 200:
        wait_for_step(client, sid, {"awaiting_user", "complete", "error"})
        pytest.fail("a second concurrent upload was accepted")
    assert second.status_code == 400


def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "healthy"}


# --- Known defects: these encode the bugs found in review. --------------------


def test_retry_does_not_duplicate_the_user_turn(client, recording, fake_externals):
    """Finding #1: a retry after a mid-pipeline failure re-runs transcription.

    The user recorded once, so the audio must be transcribed once and produce
    exactly one `user` entry in the history no matter how many times the
    later stages are retried.
    """
    sid = start_session(client)["session_id"]

    # Fail at the lyricist, i.e. after transcription has already committed.
    fake_externals.lyricist_error = RuntimeError("lyricist unavailable")

    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"error"})
    assert status["step"] == "error"

    resp = client.post(f"/api/session/{sid}/retry")
    assert resp.status_code == 200
    status = wait_for_step(client, sid, {"awaiting_user", "complete", "error"})

    assert status["step"] != "error", f"retry failed outright: {status['error']}"

    assert len(fake_externals.transcribe_calls) == 1, (
        "one recording was transcribed "
        f"{len(fake_externals.transcribe_calls)} times - the retry re-ran a "
        "step that had already succeeded (and re-billed the STT call)"
    )

    user_turns = [t for t in status["turn_history"] if t["player"] == "user"]
    assert len(user_turns) == 1, (
        f"retry duplicated the user's verse: {status['turn_history']}"
    )


def test_retry_keeps_the_ai_on_the_right_round(client, recording, fake_externals):
    """Finding #1 fallout: turn drift gives the AI the wrong instructions."""
    sid = start_session(client)["session_id"]

    fake_externals.lyricist_error = RuntimeError("lyricist unavailable")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    client.post(f"/api/session/{sid}/retry")
    wait_for_step(client, sid, {"awaiting_user", "complete", "error"})

    successful = [c for c in fake_externals.lyricist_calls][-1]
    assert "opening response" in successful["turn_instructions"], (
        "after a retry the first AI verse was given final-round instructions: "
        f"{successful['turn_instructions']!r}"
    )
