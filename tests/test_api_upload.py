"""Upload limits and session sizing.

Finding #5 (unbounded `await audio.read()`) and finding #12 (the record
window was floored while the AI verse is ceiled).
"""

import math

from conftest import TEST_BPM, start_session, wait_for_step


def _oversized_recording(size):
    return ("recording.webm", b"\x00" * size, "audio/webm")


def test_oversized_recording_is_rejected_with_413(
    client, fake_externals, monkeypatch
):
    from api.routes import session as session_route

    monkeypatch.setattr(session_route, "MAX_UPLOAD_BYTES", 4096)
    monkeypatch.setattr(session_route, "MAX_UPLOAD_MB", 0.004)

    sid = start_session(client)["session_id"]
    resp = client.post(
        f"/api/session/{sid}/recording",
        files={"audio": _oversized_recording(20_000)},
    )

    assert resp.status_code == 413, resp.text
    assert "too large" in resp.json()["detail"].lower()
    # The pipeline must not have started, and the session stays usable.
    assert fake_externals.transcribe_calls == []
    assert client.get(f"/api/session/{sid}/status").json()["step"] == "idle"


def test_recording_at_the_limit_is_accepted(client, fake_externals, monkeypatch):
    from api.routes import session as session_route

    monkeypatch.setattr(session_route, "MAX_UPLOAD_BYTES", 4096)

    sid = start_session(client)["session_id"]
    resp = client.post(
        f"/api/session/{sid}/recording",
        files={"audio": _oversized_recording(4096)},
    )

    assert resp.status_code == 200, resp.text
    wait_for_step(client, sid, {"awaiting_user"})
    assert len(fake_externals.transcribe_calls) == 1


def test_rejected_upload_leaves_no_temp_file(client, fake_externals, monkeypatch):
    import tempfile
    from pathlib import Path

    from api.routes import session as session_route

    monkeypatch.setattr(session_route, "MAX_UPLOAD_BYTES", 4096)

    before = set(Path(tempfile.gettempdir()).glob("*.webm"))
    sid = start_session(client)["session_id"]
    client.post(
        f"/api/session/{sid}/recording",
        files={"audio": _oversized_recording(20_000)},
    )
    after = set(Path(tempfile.gettempdir()).glob("*.webm"))

    assert after - before == set(), "rejected upload leaked a temp file"


def test_upload_limit_is_configurable_from_the_environment():
    """The cap is read from MAX_UPLOAD_MB (default 8MB)."""
    import importlib
    import os

    from api.routes import session as session_route

    assert session_route.MAX_UPLOAD_BYTES == int(
        session_route.MAX_UPLOAD_MB * 1024 * 1024
    )

    os.environ["MAX_UPLOAD_MB"] = "1"
    try:
        reloaded = importlib.reload(session_route)
        assert reloaded.MAX_UPLOAD_BYTES == 1024 * 1024
    finally:
        del os.environ["MAX_UPLOAD_MB"]
        importlib.reload(session_route)


def test_record_duration_is_rounded_up_to_match_the_ai_verse(client, monkeypatch):
    """Finding #12: 16 bars @90bpm is 42.67s - both sides must use 43s.

    core.generation ceils the ElevenLabs duration, so flooring here gave the
    user a shorter record window than the verse it is answering.
    """
    from api.routes import session as session_route

    monkeypatch.setattr(session_route, "BARS_PER_TURN", 16)

    session = start_session(client)
    exact_seconds = 16 * 4 * (60 / TEST_BPM)

    assert exact_seconds == 42.666666666666664  # sanity: the awkward case
    assert session["record_duration"] == math.ceil(exact_seconds) == 43
