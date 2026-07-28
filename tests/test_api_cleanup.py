"""TTL reclamation of sessions and generated audio (finding #6).

Nothing used to be reclaimed: the `sessions` dict and api/static/generated/
both grew for the lifetime of the process. Creation of a new session now
sweeps both.
"""

import time

from conftest import start_session, upload_turn, wait_for_step


def _make_session(session_id, age_seconds=0.0, **kwargs):
    from api.services.pipeline import SessionState, sessions

    session = SessionState(
        session_id=session_id, bpm=90, bars_per_turn=2, turns_per_player=2, **kwargs
    )
    session.last_activity = time.time() - age_seconds
    sessions[session_id] = session
    return session


def test_creating_a_session_sweeps_expired_ones(client, monkeypatch):
    import api.services.pipeline as pipeline_mod
    from api.services.pipeline import sessions

    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 60)

    _make_session("stale", age_seconds=600)
    _make_session("fresh", age_seconds=1)

    new_id = start_session(client)["session_id"]

    assert "stale" not in sessions, "an expired session was never reclaimed"
    assert "fresh" in sessions
    assert new_id in sessions


def test_expired_session_status_becomes_404(client, monkeypatch):
    import api.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 60)
    _make_session("stale", age_seconds=600)

    start_session(client)
    assert client.get("/api/session/stale/status").status_code == 404


def test_polling_keeps_a_session_alive(client, recording, monkeypatch):
    """The TTL is idle time, not absolute age - an active battle must survive."""
    import api.services.pipeline as pipeline_mod
    from api.services.pipeline import sessions

    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 60)

    sid = start_session(client)["session_id"]
    sessions[sid].last_activity = time.time() - 600  # long idle
    client.get(f"/api/session/{sid}/status")  # ...but the player is still here

    start_session(client)
    assert sid in sessions, "an actively polled session was swept away"


def test_running_sessions_are_never_swept(client, monkeypatch):
    import api.services.pipeline as pipeline_mod
    from api.services.pipeline import sessions

    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 60)
    session = _make_session("busy", age_seconds=600)
    session.try_acquire_run()  # stands in for a live pipeline thread
    try:
        start_session(client)
        assert "busy" in sessions, "a session with a live pipeline thread was dropped"
    finally:
        session.release_run()


def test_old_generated_audio_is_deleted(client, monkeypatch, tmp_path):
    import api.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "GENERATED_AUDIO_DIR", tmp_path)
    monkeypatch.setattr(pipeline_mod, "GENERATED_AUDIO_TTL_SECONDS", 60)

    old = tmp_path / "old_turn2.mp3"
    old.write_bytes(b"ID3old")
    import os

    stale = time.time() - 600
    os.utime(old, (stale, stale))

    recent = tmp_path / "recent_turn2.mp3"
    recent.write_bytes(b"ID3recent")

    other = tmp_path / "keep.txt"
    other.write_text("not generated audio")

    start_session(client)

    assert not old.exists(), "an expired generated mp3 was kept forever"
    assert recent.exists()
    assert other.exists(), "cleanup deleted a non-mp3 file"


def test_cleanup_reports_what_it_removed(monkeypatch, tmp_path):
    import api.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "GENERATED_AUDIO_DIR", tmp_path)
    monkeypatch.setattr(pipeline_mod, "GENERATED_AUDIO_TTL_SECONDS", 60)
    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 60)

    _make_session("stale", age_seconds=600)
    result = pipeline_mod.cleanup_expired()

    assert result == {"sessions_removed": 1, "files_removed": 0}


def test_finished_battles_are_eventually_reclaimed(
    client, recording, fake_externals, monkeypatch
):
    """End to end: a completed battle does not pin memory forever."""
    import api.services.pipeline as pipeline_mod
    from api.services.pipeline import sessions

    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"awaiting_user"})
    upload_turn(client, sid, recording)
    wait_for_step(client, sid, {"complete"})

    monkeypatch.setattr(pipeline_mod, "SESSION_TTL_SECONDS", 0)
    sessions[sid].last_activity = time.time() - 1

    start_session(client)
    assert sid not in sessions
