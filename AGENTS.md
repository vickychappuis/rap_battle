# AGENTS.md — Rap Battle AI (POC)

## Project overview

This project is an app for hip-hoppers to battle rap against AI.

High-level flow (target architecture):

1. User spits bars (audio input).
2. Speech → text using OpenAI STT (transcription). ✅ implemented
3. An AI agent generates a rap response (lyrics). ✅ implemented
4. Another agent converts the lyrics into an ElevenLabs-ready prompt (lyrics divided per beat). ✅ implemented
5. ElevenLabs generates audio/music from the formatted prompt. ✅ implemented
6. Start a base instrumental immediately when the user starts, keep it playing through the whole pipeline, then insert the ElevenLabs audio at the next best beat/bar moment. ✅ implemented
7. **NEW (next):** Web front-end that shows the pipeline + session playback in real time. 🔜 next

Current focus is a **POC**. We’re building incrementally and keeping the scope tight.

## Technologies

### Backend
- Python
- OpenAI
  - Speech-to-text (STT) for transcribing the user’s spoken bars
  - Text generation for rap responses
- ElevenLabs (audio/music generation)
- LangChain (agent/prompt orchestration)

### Frontend (NEW)
- React (web UI)
- Browser audio:
  - Record user audio (mic)
  - Play the base instrumental continuously during the session
  - Insert/play the ElevenLabs response at the scheduled beat/bar moment

## Current focus (web UI that shows the pipeline)

We don’t have a frontend yet. Next step is a minimal React web app that exposes what we already have:

**What the web app should do (POC scope):**
- Start a “battle session”
- Let the user record spoken bars
- Show pipeline progress (STT → AI lyrics → beat formatting → ElevenLabs generation)
- Keep the **base instrumental playing** through the entire pipeline
- When ElevenLabs audio is ready, play it at the **next scheduled beat/bar moment** (BPM-based placement)
- Display:
  - transcription text
  - AI response lyrics
  - formatted “per beat” prompt (optional but useful for debugging)

**What the web app should NOT do yet:**
- No accounts/auth
- No feeds/sharing
- No session history library
- No extra features beyond “show what we have for now”

## Audio behavior (frontend expectations)

- The frontend should treat the session as a single continuous musical timeline.
- Base instrumental starts immediately when the session starts and does not stop during:
  - recording
  - transcription
  - AI generation
  - formatting
  - ElevenLabs audio generation
- When the backend indicates the ElevenLabs audio is ready, the frontend:
  - stores it (or receives a URL)
  - waits until the next planned musical boundary (beat/bar based on known BPM)
  - plays it cleanly on the boundary

Implementation note (POC): the UI can initially rely on simple timing (BPM + session start time). If tighter sync is needed later, we can move scheduling to a more precise audio-clock approach.

## Status

- AI rap response generation: ✅ implemented
- ElevenLabs prompt formatting (per beat): ✅ implemented
- ElevenLabs audio/music generation (API): ✅ implemented
- OpenAI STT (audio → text): ✅ implemented
- Base instrumental session playback + scheduled ElevenLabs insert (BPM-based): ✅ implemented
- Web frontend (React) to show the pipeline + session playback: 🔜 next

## Repository conventions

- Keep agent logic modular and easy to test.
- Keep prompting/templates easy to locate and edit.
- Prefer clear, small changes over large refactors (POC pace).
- **Frontend:** follow `visual_style_guide.md` exactly. Do not expand or add new design rules—just implement what exists.

## Documentation

- All documentation related to changes, implementations, and project decisions should be placed in:
  `/Users/victoriachappuis/personal/rap_battle/changes_documentation`

## Dependencies

- All Python dependencies must be declared in `requirements.txt`.
- Avoid adding new dependencies unless the task explicitly requires it.
- Frontend dependencies should be kept minimal (POC).

## Configuration & secrets

- API keys should come from environment variables (never committed).
  - `OPENAI_API_KEY`
  - `ELEVENLABS_API_KEY` (and any other ElevenLabs-required env vars)
- Avoid logging sensitive user content by default (including raw audio and full transcriptions).

## Frontend development/design notes

- Use React as the framework.
- Make use of components.
- Audio is a core feature of the web experience, not an afterthought.
- The primary goal is to **visualize the pipeline state** and **experience the continuous beat + scheduled AI insert**.
