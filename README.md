# Rap Battle AI

Battle rap against an AI opponent in the browser. You spit bars into your mic;
the app transcribes them, writes a timed comeback, turns it into an a cappella
vocal, and drops it back over a looping beat — in time with the bar. After the
last round an AI judge picks a winner.

This is a proof of concept: sessions live in memory and there are no accounts.

## How it works

A battle turn runs through a short pipeline:

1. **Transcribe** — the user's recording → text (OpenAI transcription).
2. **Write bars** — a LangChain "lyricist" agent writes a timed response to the
   opponent's bars, aware of the battle so far.
3. **Build the grid** — pure-Python step maps the bars onto a beat-by-beat
   timing grid and produces the prompt for audio generation.
4. **Generate audio** — ElevenLabs turns the prompt into an a cappella vocal.
5. **Judge** — after the final turn, an AI judge scores the battle.

The frontend keeps a base instrumental looping the whole time (Web Audio) and
schedules the AI vocal to start on the next bar boundary, so the response lands
in time with the beat.

## Architecture

```
frontend/            React + TypeScript + Vite (Web Audio, mic recording)
api/                 FastAPI web layer
  routes/session.py  Session + recording + status endpoints
  services/          Pipeline orchestration (background thread)
core/                Domain logic (framework-agnostic)
  generation.py      Lyricist agent + ElevenLabs music generation
  grid_builder.py    Deterministic beat-grid + prompt builder
  stt.py             Speech-to-text
  models.py          Pydantic schemas
  prompts/           Lyricist and judge prompt templates
assets/tracks/       Base instrumental
```

The frontend talks to the API under `/api` and loads audio from `/static`; in
dev, Vite proxies both to the backend.

## Running locally

The quickest path is Docker Compose:

```bash
cp .env.example .env   # then fill in OPENAI_API_KEY and ELEVENLABS_API_KEY
docker compose up
```

- Frontend: http://localhost:5173
- API: http://localhost:8000 (docs at `/docs`)

### Without Docker

Backend:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Copy `.env.example` to `.env`. `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` are
required; everything else has sensible defaults (see the comments in
`.env.example`). Set `MOCK_ELEVENLABS=true` with a `MOCK_RESPONSE_PATH` to
develop without spending ElevenLabs credits.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/session` | Start a battle, get config + base track URL |
| `POST` | `/api/session/{id}/recording` | Upload a turn's audio, kick off the pipeline |
| `POST` | `/api/session/{id}/retry` | Retry a failed turn |
| `GET`  | `/api/session/{id}/status` | Poll pipeline state, lyrics, audio URL, result |
| `GET`  | `/health` | Health check |

## License

MIT
