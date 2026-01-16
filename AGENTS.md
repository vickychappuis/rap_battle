# AGENTS.md — Rap Battle AI (POC)

## Project overview

This project is an app for hip-hoppers to battle rap against AI.

High-level flow (target architecture):

1. User spits bars (audio input).
2. Speech → text using OpenAI STT (transcription). ✅ implemented
3. An AI agent generates a rap response (lyrics). ✅ implemented
4. Another agent converts the lyrics into an ElevenLabs-ready prompt (lyrics divided per beat). ✅ implemented
5. ElevenLabs generates audio/music from the formatted prompt. ✅ implemented
6. **NEW (next):** Start a base instrumental immediately when the user starts, keep it playing through the whole pipeline, then insert the ElevenLabs audio at the next best beat/bar moment. 🔜 next

Current focus is a **POC**. We’re building incrementally and keeping the scope tight.

## Technologies

- Python
- OpenAI
  - Speech-to-text (STT) for transcribing the user’s spoken bars
  - Text generation for rap responses
- ElevenLabs (audio/music generation)
- LangChain (agent/prompt orchestration)

## Current focus (base track playback + scheduled insert)

We want a consistent “battle session” experience where the same instrumental plays continuously:

- When the user begins recording / the pipeline starts, **start playing the base hip-hop instrumental immediately**.
- The base track **keeps playing** while we transcribe (STT), generate the rap response, format the prompt, and call ElevenLabs.
- When the ElevenLabs audio is ready, **save it**, then **wait to place/play it at the next best moment** (e.g., next beat or next bar).
  - This moment should be **planned/recorded** using the known BPM (we don’t care if the user is perfectly on beat; we just want predictable placement).
- The goal is that the user can rap over the beat, and the AI response comes in cleanly at a natural musical boundary.

## Status

- AI rap response generation: ✅ implemented
- ElevenLabs prompt formatting (per beat): ✅ implemented
- ElevenLabs audio/music generation (API): ✅ implemented
- OpenAI STT (audio → text): ✅ implemented
- **Base instrumental session playback + scheduled ElevenLabs insert (BPM-based): 🔜 next**

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


# For Frontend development/design
You MUST follow visual_style_guide.md and keep good practices. Use React as your framework. Make use of components. Consider the audio feature is n important part of this web.