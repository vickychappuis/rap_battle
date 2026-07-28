# Rap Battle AI

[![CI](https://github.com/vickychappuis/rap_battle/actions/workflows/ci.yml/badge.svg)](https://github.com/vickychappuis/rap_battle/actions/workflows/ci.yml)

**Live demo: [raparena.vickychappuis.dev](https://raparena.vickychappuis.dev)**

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
tests/               Backend suite (external APIs stubbed)
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

Requires Python 3.12+ and Node 20+.

Backend:

```bash
pip install -r requirements.txt        # or requirements-dev.txt to run the tests
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

Missing keys don't stop the server: it starts, logs which ones are absent, and
`/health` still answers — battles just fail until you set them.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite drives real battles over the real HTTP API and the real background
pipeline, stubbing only the three external boundaries (OpenAI transcription,
the lyricist chain, ElevenLabs). It costs nothing to run and needs no API keys.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/session` | Start a battle, get config + base track URL |
| `POST` | `/api/session/{id}/recording` | Upload a turn's audio, kick off the pipeline |
| `POST` | `/api/session/{id}/retry` | Resume a failed turn from the stage that failed |
| `GET`  | `/api/session/{id}/status` | Poll pipeline state, lyrics, audio URL, result |
| `GET`  | `/health` | Health check |

Notable status codes: `413` if a recording exceeds `MAX_UPLOAD_MB`, `409` if a
turn is already being processed for that session, `429` when the global rate
limit trips.

## Limits

This is a POC and the guard rails are deliberately blunt:

- Sessions live in memory, so a restart drops every battle in progress. They
  are reclaimed after `SESSION_TTL_SECONDS` idle, along with their generated
  audio.
- The rate limit (4/hour, 15/day) is **global, not per-user** — it is a spend
  cap on the API keys, not abuse protection. One client can exhaust it for
  everyone.
- There are no accounts and no authentication.
- The user's transcribed bars are interpolated straight into the lyricist
  prompt, and nothing moderates what either side says. It is a battle-rap toy,
  not a system hardened against prompt injection or abusive content.

## Deploying your own copy

The demo runs the frontend on Vercel and the API on a container host, with the
frontend proxying to the API so the browser only ever talks to one origin.

If you fork this, **change the backend URL in `frontend/vercel.json`** — its
`/api` and `/static` rewrites point at this project's own backend, and left as
they are your deployment will send its traffic (and its bill) there. It will
also share this deployment's global rate limit, so battles will fail for
everyone once the daily cap trips.

The API needs `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, and `ALLOWED_ORIGINS` set
to your frontend's origin. `api/Dockerfile` builds it from the repo root.

## License

Code is MIT — see [LICENSE](LICENSE).

The bundled assets are **not** covered by that grant: the base instrumental
(`assets/tracks/`) and the artwork (`frontend/public/`) are used under licences
held by the author and cannot be redistributed. Swap them for your own if you
fork this.
