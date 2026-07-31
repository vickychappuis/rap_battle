"""Configuration-driven behaviour of the pipeline.

Covers finding #9 (mock mode silently falling through to the billed API),
#11 (status never exposed timing), #13 (sensitive content logged by default),
#14 (hardcoded judge model) and #15 (TURNS_PER_PLAYER at the HTTP level).
"""

import logging

import pytest

from conftest import start_session, upload_turn, wait_for_step


# --- Finding #9: mock mode must fail loudly -----------------------------------


def test_mock_mode_without_a_path_fails_instead_of_calling_elevenlabs(
    client, recording, fake_externals, monkeypatch
):
    monkeypatch.setenv("MOCK_ELEVENLABS", "true")
    monkeypatch.delenv("MOCK_RESPONSE_PATH", raising=False)

    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"error"})

    assert "MOCK_RESPONSE_PATH" in status["error"]
    assert fake_externals.music_calls == [], (
        "mock mode fell through to the real (billed) ElevenLabs call"
    )


def test_mock_mode_with_a_missing_file_fails_clearly(
    client, recording, fake_externals, monkeypatch, tmp_path
):
    missing = tmp_path / "nope.mp3"
    monkeypatch.setenv("MOCK_ELEVENLABS", "true")
    monkeypatch.setenv("MOCK_RESPONSE_PATH", str(missing))

    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"error"})

    assert "nope.mp3" in status["error"]
    assert "does not exist" in status["error"]
    assert fake_externals.music_calls == []


def test_mock_mode_with_a_valid_file_serves_that_audio(
    client, recording, fake_externals, monkeypatch, tmp_path
):
    mock_mp3 = tmp_path / "canned.mp3"
    mock_mp3.write_bytes(b"ID3canned-response")
    monkeypatch.setenv("MOCK_ELEVENLABS", "true")
    monkeypatch.setenv("MOCK_RESPONSE_PATH", str(mock_mp3))

    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"awaiting_user"})

    assert fake_externals.music_calls == []
    assert client.get(status["ai_audio_url"]).content == b"ID3canned-response"


# --- Finding #14: judge model is configurable ---------------------------------


def _run_full_battle(client, recording):
    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"awaiting_user"})
    upload_turn(client, sid, recording)
    return wait_for_step(client, sid, {"complete"})


def test_judge_uses_its_own_model_env_var(
    client, recording, fake_externals, monkeypatch
):
    monkeypatch.setenv("OPENAI_JUDGE_MODEL", "gpt-4.1-mini")
    # The lyricist model must stay independent of it.
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")

    _run_full_battle(client, recording)

    assert fake_externals.judge_calls[0]["model"] == "gpt-4.1-mini"


def test_judge_model_defaults_to_gpt_4o_mini(
    client, recording, fake_externals, monkeypatch
):
    monkeypatch.delenv("OPENAI_JUDGE_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "some-reasoning-model")

    _run_full_battle(client, recording)

    assert fake_externals.judge_calls[0]["model"] == "gpt-4o-mini", (
        "the judge should not inherit OPENAI_MODEL (it is a plain chat call)"
    )


# --- Finding #13: sensitive content is not logged by default ------------------


def test_transcription_and_lyrics_are_not_logged_by_default(
    client, recording, fake_externals, monkeypatch, caplog
):
    monkeypatch.delenv("DEBUG_LOG_CONTENT", raising=False)

    with caplog.at_level(logging.INFO):
        sid = start_session(client)["session_id"]
        upload_turn(client, sid, recording)
        status = wait_for_step(client, sid, {"awaiting_user"})

    assert status["transcription"] not in caplog.text, "the transcription was logged"
    assert status["lyrics"] not in caplog.text, "the generated lyrics were logged"
    # ...but the non-sensitive progress/timing logs are still there.
    assert "TIMING SUMMARY" in caplog.text


def test_debug_flag_re_enables_content_logging(
    client, recording, fake_externals, monkeypatch, caplog
):
    monkeypatch.setenv("DEBUG_LOG_CONTENT", "true")

    with caplog.at_level(logging.INFO):
        sid = start_session(client)["session_id"]
        upload_turn(client, sid, recording)
        status = wait_for_step(client, sid, {"awaiting_user"})

    assert status["transcription"] in caplog.text
    assert status["lyrics"] in caplog.text


# --- Finding #11: timing is exposed on /status --------------------------------


def test_status_exposes_timing_for_the_current_turn(
    client, recording, fake_externals
):
    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"awaiting_user"})

    timing = status["timing"]
    assert timing is not None, "SessionStatus.timing was declared but never filled"
    assert set(timing) == {
        "transcription_seconds",
        "lyricist_seconds",
        "grid_builder_seconds",
        "audio_generation_seconds",
        "total_seconds",
    }
    assert timing == status["turn_history"][-1]["timing"]


def test_timing_survives_a_retry_without_double_counting(
    client, recording, fake_externals
):
    """A resumed stage keeps the timing measured on its successful run."""
    sid = start_session(client)["session_id"]
    fake_externals.music_error = RuntimeError("elevenlabs 500")
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"error"})

    client.post(f"/api/session/{sid}/retry")
    status = wait_for_step(client, sid, {"awaiting_user"})

    timing = status["timing"]
    assert "transcription_seconds" in timing, (
        "timing from the first attempt was thrown away by the retry"
    )
    assert timing["total_seconds"] == pytest.approx(
        sum(
            timing[k]
            for k in (
                "transcription_seconds",
                "lyricist_seconds",
                "grid_builder_seconds",
                "audio_generation_seconds",
            )
        ),
        abs=0.01,
    )


# --- Finding #15: TURNS_PER_PLAYER drives the round instructions ---------------


@pytest.mark.parametrize("turns_per_player", [3], indirect=True)
def test_three_round_battle_gets_opening_middle_final_instructions(
    client, recording, fake_externals
):
    session = start_session(client)
    sid = session["session_id"]
    assert session["turns_per_player"] == 3

    for expected_step in ("awaiting_user", "awaiting_user", "complete"):
        assert upload_turn(client, sid, recording).status_code == 200
        status = wait_for_step(client, sid, {expected_step})

    assert status["step"] == "complete"
    assert len(fake_externals.lyricist_calls) == 3

    first, middle, final = (
        call["turn_instructions"] for call in fake_externals.lyricist_calls
    )
    assert "opening response" in first
    assert "Middle of the battle" in middle, (
        f"round 2 of 3 got non-scaling instructions: {middle!r}"
    )
    assert "round 2 of 3" in middle
    assert "Final round" in final

    history = [(t["turn_number"], t["player"]) for t in status["turn_history"]]
    assert history == [
        (1, "user"), (2, "ai"), (3, "user"), (4, "ai"), (5, "user"), (6, "ai")
    ]
