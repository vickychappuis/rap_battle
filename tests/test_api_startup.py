"""Startup robustness: the app must import and answer /health without keys.

Finding #3: `PipelineService()` used to build the LangChain client at module
scope, so a missing OPENAI_API_KEY turned into an import-time crash loop with
no health endpoint and no readable error.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Importing the app in a fresh interpreter is slow (LangChain), so the import
# check and the /health check share a single subprocess.
_STARTUP_SCRIPT = """
import json
from fastapi.testclient import TestClient
import api.main

print("IMPORTED")
with TestClient(api.main.app) as c:
    print("HEALTH " + json.dumps(c.get("/health").json()))
"""


def _run_without_openai_key(script: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    # .env would put the key back; point dotenv at a directory with no .env.
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(  # noqa: PLW1510 - callers assert on returncode themselves
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _skip_if_local_dotenv_provides_a_key():
    """A developer's own .env would hand the subprocess a key anyway."""
    if (PROJECT_ROOT / ".env").exists():
        pytest.skip("a local .env would repopulate OPENAI_API_KEY in the subprocess")


def test_app_imports_and_serves_health_without_an_openai_key():
    """The whole point of #3: no key must not mean no app."""
    _skip_if_local_dotenv_provides_a_key()
    result = _run_without_openai_key(_STARTUP_SCRIPT)

    assert result.returncode == 0, (
        f"api.main without OPENAI_API_KEY failed:\n{result.stderr}"
    )
    assert "IMPORTED" in result.stdout, "importing api.main raised"
    assert 'HEALTH {"status": "healthy"}' in result.stdout, (
        f"/health did not answer without a key:\n{result.stdout}"
    )


def test_service_construction_does_not_build_the_llm(monkeypatch):
    """Constructing the service must not touch the LLM factory at all."""
    import api.services.pipeline as pipeline_mod

    def _boom(*args, **kwargs):
        raise AssertionError("create_lyricist_agent called during construction")

    monkeypatch.setattr(pipeline_mod, "create_lyricist_agent", _boom)
    service = pipeline_mod.PipelineService()  # must not raise
    assert service._lyricist_chain is None


def test_lyricist_is_built_once_on_first_use(monkeypatch):
    import api.services.pipeline as pipeline_mod

    builds = []

    def _fake_factory(*args, **kwargs):
        builds.append(1)
        return "chain", "parser"

    monkeypatch.setattr(pipeline_mod, "create_lyricist_agent", _fake_factory)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")

    service = pipeline_mod.PipelineService()
    assert service.lyricist_chain == "chain"
    assert service.lyricist_parser == "parser"
    assert service.lyricist_chain == "chain"
    assert len(builds) == 1, "the lyricist chain was rebuilt on every access"


def test_missing_key_fails_with_an_explicit_message(monkeypatch):
    """No key at use time gives a readable error, not an opaque OpenAIError."""
    import api.services.pipeline as pipeline_mod

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = pipeline_mod.PipelineService()

    with pytest.raises(RuntimeError) as excinfo:
        _ = service.lyricist_chain

    assert "OPENAI_API_KEY" in str(excinfo.value)


def test_missing_key_surfaces_as_a_session_error(client, recording, monkeypatch):
    """A key that disappears at runtime becomes a retryable turn error."""
    from conftest import start_session, upload_turn, wait_for_step

    import api.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod.pipeline_service, "_lyricist_chain", None)
    monkeypatch.setattr(pipeline_mod.pipeline_service, "_lyricist_parser", None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    sid = start_session(client)["session_id"]
    upload_turn(client, sid, recording)
    status = wait_for_step(client, sid, {"error"})

    assert "OPENAI_API_KEY" in status["error"]
