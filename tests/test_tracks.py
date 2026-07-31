"""The base-track catalog: BPM comes from the filename, never from an env var."""

import math

import pytest
from conftest import TEST_BARS, start_session

from api import tracks as tracks_mod
from api.tracks import Track, choose_track, discover_tracks


def test_discovery_parses_bpm_from_the_filename(tmp_path):
    (tmp_path / "base_90bpm.mp3").write_bytes(b"ID3")
    (tmp_path / "chill_120bpm.mp3").write_bytes(b"ID3")

    tracks = discover_tracks(tmp_path)

    assert tracks == [
        Track("base_90bpm.mp3", 90),
        Track("chill_120bpm.mp3", 120),
    ]


def test_discovery_ignores_files_without_a_bpm_in_the_name(tmp_path):
    (tmp_path / "base_90bpm.mp3").write_bytes(b"ID3")
    (tmp_path / "mystery_track.mp3").write_bytes(b"ID3")
    (tmp_path / "notes.txt").write_text("not audio")

    tracks = discover_tracks(tmp_path)

    assert tracks == [Track("base_90bpm.mp3", 90)]


def test_discovery_of_a_missing_directory_is_empty(tmp_path):
    assert discover_tracks(tmp_path / "nope") == []


def test_the_repo_catalog_contains_the_bundled_track():
    """The real assets/tracks/ dir must always yield a usable catalog."""
    tracks = discover_tracks()
    assert Track("base_90bpm.mp3", 90) in tracks


def test_choose_track_fails_loudly_on_an_empty_catalog(monkeypatch):
    monkeypatch.setattr(tracks_mod, "TRACKS", [])
    with pytest.raises(RuntimeError, match="No base tracks"):
        choose_track()


def test_session_bpm_and_track_url_come_from_the_same_track(
    client, monkeypatch
):
    """The response's bpm and base_track_url can never disagree."""
    monkeypatch.setattr(
        tracks_mod, "TRACKS", [tracks_mod.Track("fast_140bpm.mp3", 140)]
    )

    session = start_session(client)

    assert session["bpm"] == 140
    assert session["base_track_url"] == "/static/tracks/fast_140bpm.mp3"
    # The record window scales with the track's tempo (TEST_BARS bars at 140).
    assert session["record_duration"] == math.ceil(TEST_BARS * 4 * 60 / 140)
