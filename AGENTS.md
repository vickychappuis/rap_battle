# AGENTS.md — Rap Battle AI (POC)

## Project overview

This project is an app for hip-hoppers to battle rap against AI.

High-level flow (target architecture):

1. User performs bars (eventually speech → text).
2. An AI agent generates a rap response (lyrics).
3. Another agent converts the lyrics into a prompt formatted for ElevenLabs (lyrics divided per beat).
4. (Later) ElevenLabs generates audio.

Current focus is a **POC**. We’re building incrementally and keeping the scope tight.

## Technologies

- Python
- OpenAI (text generation)
- ElevenLabs (voice/music side; for now we only format prompts for it)
- LangChain (agent/prompt orchestration)

## Current work (text agents only)

For now, we are only preparing the text agents:

- Agent that reads the user’s written bars and produces response lyrics.
- Agent that turns those lyrics into an ElevenLabs-ready prompt (divided per beat).

## Repository conventions

- Keep agent logic modular and easy to test.
- Keep prompting/templates easy to locate and edit.
- Prefer clear, small changes over large refactors (POC pace).

## Documentation

- All documentation related to changes, implementations, and project decisions should be placed in `/Users/victoriachappuis/personal/rap_battle/changes_documentation`.

## Dependencies

- All Python dependencies must be declared in `requirements.txt`.
- Avoid adding new dependencies unless the task explicitly requires it.

## Configuration & secrets

- API keys should come from environment variables (never committed).
- Avoid logging sensitive user content by default.
