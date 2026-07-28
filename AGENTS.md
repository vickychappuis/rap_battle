# AGENTS.md — Rap Battle AI (POC)

## Project overview

A web app for battling rap against an AI opponent.

Turn flow:

1. User spits bars (audio input, recorded in the browser).
2. Speech → text via OpenAI transcription.
3. A LangChain agent writes a rap response (lyrics), aware of the battle so far.
4. A pure-Python step maps the lyrics onto a beat-by-beat grid and builds the
   audio-generation prompt.
5. ElevenLabs generates the a cappella vocal.
6. A base instrumental loops throughout; the AI vocal is scheduled to start on
   the next bar boundary so it lands in time with the beat.
7. After the final turn, an AI judge picks a winner.

This is a **POC**: sessions are in-memory, there are no accounts, and scope is
kept tight.

## Technologies

**Backend** — Python, FastAPI. OpenAI (transcription + lyric generation),
ElevenLabs (audio generation), LangChain (prompt orchestration).

**Frontend** — React + TypeScript + Vite, Tailwind. Browser audio: record the
mic, loop the base instrumental, and schedule the AI response on a bar boundary
using the Web Audio clock.

## Audio behavior

- The session is a single continuous musical timeline.
- The base instrumental starts when the session starts and keeps playing through
  recording, transcription, generation, and formatting.
- When the backend reports the AI vocal is ready, the frontend waits for the
  next bar boundary (BPM-based) and plays it cleanly on the beat.

## Conventions

- Keep agent logic modular and prompts easy to locate and edit
  (`core/prompts/`). Domain logic lives in `core/`; `api/` is the web layer.
- Prefer small, clear changes over large refactors (POC pace).
- **Frontend:** follow `visual_style_guide.md`; don't add new design rules.
- Keep frontend dependencies minimal.
- Python dependencies belong in `requirements.txt` (test-only ones in
  `requirements-dev.txt`); avoid adding new ones unless a task requires it.
  Both are pinned with `~=` at major.minor — bumping a minor is a deliberate act.
- Backend changes should come with tests. `python -m pytest` runs battles
  through the real API with only the external services stubbed, so it is fast
  and free; add to `tests/` rather than testing by hand.

## Configuration & secrets

- API keys come from environment variables and are never committed
  (`OPENAI_API_KEY`, `ELEVENLABS_API_KEY`). See `.env.example`.
- Avoid logging sensitive user content by default (raw audio, full
  transcriptions).
