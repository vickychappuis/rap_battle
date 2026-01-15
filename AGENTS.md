# AGENTS.md — Rap Battle AI (POC)

## Project overview

This project is an app for hip-hoppers to battle rap against AI.

High-level flow (target architecture):

1. User spits bars (audio input).
2. Speech → text using OpenAI STT (transcription).
3. An AI agent generates a rap response (lyrics). ✅ implemented
4. Another agent converts the lyrics into an ElevenLabs-ready prompt (lyrics divided per beat). ✅ implemented
5. ElevenLabs generates audio/music from the formatted prompt. ✅ implemented

Current focus is a **POC**. We’re building incrementally and keeping the scope tight.

## Technologies

- Python
- OpenAI
  - Speech-to-text (STT) for transcribing the user’s spoken bars
  - Text generation for rap responses
- ElevenLabs (audio/music generation)
- LangChain (agent/prompt orchestration)

## Current focus (speech input + STT)

Speech-to-text (STT) via OpenAI is now implemented:

- Capture/accept the user's recorded bars (audio) via microphone or file
- Transcribe audio → text using OpenAI Whisper API
- Feed transcription into the existing battle pipeline

## Status

- AI rap response generation: ✅ implemented
- ElevenLabs prompt formatting (per beat): ✅ implemented
- ElevenLabs audio/music generation (API): ✅ implemented
- OpenAI STT (audio → text): ✅ implemented

## Repository conventions

- Keep agent logic modular and easy to test.
- Keep prompting/templates easy to locate and edit.
- Prefer clear, small changes over large refactors (POC pace).

## Documentation

- All documentation related to changes, implementations, and project decisions should be placed in:
  `/Users/victoriachappuis/personal/rap_battle/changes_documentation`

## Dependencies

- All Python dependencies must be declared in `requirements.txt`.
- Avoid adding new dependencies unless the task explicitly requires it.

## Configuration & secrets

- API keys should come from environment variables (never committed).
  - `OPENAI_API_KEY`
  - `ELEVENLABS_API_KEY` (and any other ElevenLabs-required env vars)
- Avoid logging sensitive user content by default (including raw audio and full transcriptions).
