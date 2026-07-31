"""Tests for the lyricist agent config, output validation and music writing."""

import logging
import math
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from core import generation
from core.generation import (
    create_lyricist_agent,
    generate_music,
    validate_lyricist_output,
)
from core.models import LyricistOutput


def _llm_from_chain(chain):
    return next(step for step in chain.steps if isinstance(step, ChatOpenAI))


# --- #2: no dead temperature config ----------------------------------------


def test_lyricist_agent_does_not_set_temperature():
    """Reasoning models drop temperature, so it must not be configured."""
    chain, _ = create_lyricist_agent("gpt-5-mini")
    llm = _llm_from_chain(chain)

    assert llm.temperature is None
    payload = llm._get_request_payload([HumanMessage(content="hi")])
    assert "temperature" not in payload


def test_lyricist_agent_still_requests_json_output():
    chain, _ = create_lyricist_agent("gpt-5-mini")
    payload = _llm_from_chain(chain)._get_request_payload(
        [HumanMessage(content="hi")]
    )

    assert payload["model"] == "gpt-5-mini"
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"]["format"] == {"type": "json_object"}


# --- #10: validation logs the post-coercion count --------------------------


def test_validation_logs_the_truncated_count(caplog):
    output = LyricistOutput(bars=[f"bar {i}" for i in range(6)])
    with caplog.at_level(logging.INFO):
        validate_lyricist_output(output, 4)

    assert len(output.bars) == 4
    assert "Validation passed: 4 bars" in caplog.text
    assert "Validation passed: 6 bars" not in caplog.text


def test_validation_logs_the_padded_count(caplog):
    output = LyricistOutput(bars=["one", "two"])
    with caplog.at_level(logging.INFO):
        validate_lyricist_output(output, 4)

    assert len(output.bars) == 4
    assert "Validation passed: 4 bars" in caplog.text
    assert "Validation passed: 2 bars" not in caplog.text


def test_validation_word_count_matches_the_final_bars(caplog):
    output = LyricistOutput(bars=["a b c", "d e f", "g h i"])
    with caplog.at_level(logging.INFO):
        validate_lyricist_output(output, 2)

    assert "Validation passed: 2 bars, 6 total words" in caplog.text


def test_validation_raises_when_too_few_bars_to_pad():
    output = LyricistOutput(bars=["only one"])
    with pytest.raises(ValueError, match="too few to pad"):
        validate_lyricist_output(output, 8)


# --- #8: generate_music writes to the requested destination ----------------


class _FakeResponse:
    content = b"ID3fake-mp3"

    def raise_for_status(self):
        pass


@pytest.fixture
def captured_requests(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, **kwargs):
        calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse()

    monkeypatch.setattr(generation.requests, "post", fake_post)
    return calls


def test_generate_music_writes_to_the_given_destination(captured_requests, tmp_path):
    dest = tmp_path / "generated" / "session123_turn2.mp3"

    result = generate_music("prompt", 5.0, "key", output_path=dest)

    assert Path(result) == dest
    assert dest.read_bytes() == b"ID3fake-mp3"


def test_generate_music_accepts_a_string_destination(captured_requests, tmp_path):
    dest = tmp_path / "out.mp3"

    result = generate_music("prompt", 5.0, "key", output_path=str(dest))

    assert Path(result) == dest


def test_generate_music_destinations_do_not_collide(captured_requests, tmp_path):
    """Two battles in the same second used to overwrite each other."""
    first = generate_music("a", 5.0, "key", output_path=tmp_path / "a.mp3")
    second = generate_music("b", 5.0, "key", output_path=tmp_path / "b.mp3")

    assert first != second
    assert Path(first).exists() and Path(second).exists()
    assert not (tmp_path / "music_output").exists()


def test_generate_music_defaults_to_the_legacy_location(
    captured_requests, tmp_path, monkeypatch
):
    """The pipeline still calls it without a destination; keep that working."""
    monkeypatch.chdir(tmp_path)

    result = generate_music("prompt", 5.0, "key")

    path = Path(result)
    assert path.parent == Path("music_output")
    assert path.exists()
    assert path.suffix == ".mp3"


def test_generate_music_rounds_duration_up_to_whole_seconds(
    captured_requests, tmp_path
):
    generate_music("prompt", 5.33, "key", output_path=tmp_path / "x.mp3")

    payload = captured_requests[0]["json"]
    assert payload["music_length_ms"] == math.ceil(5.33) * 1000 == 6000
    assert payload["prompt"] == "prompt"
