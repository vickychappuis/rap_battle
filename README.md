# Rap Battle AI

[![CI](https://github.com/vickychappuis/rap_battle/actions/workflows/ci.yml/badge.svg)](https://github.com/vickychappuis/rap_battle/actions/workflows/ci.yml)

**Live demo: [raparena.vickychappuis.dev](https://raparena.vickychappuis.dev)**

Battle rap against an AI opponent in the browser. You spit bars into your mic;
the app transcribes them, writes a timed comeback, turns it into an a cappella
vocal, and drops it back over a looping beat — in time with the bar. After the
last round an AI judge picks a winner.

A battle turn runs through a short pipeline: transcribe the recording (OpenAI),
write timed bars (a LangChain "lyricist" agent), map them onto a beat grid
(pure Python), generate the vocal (ElevenLabs), and — after the final turn —
judge the battle. The frontend loops the instrumental with Web Audio and
schedules the AI vocal on the next bar boundary so it lands on beat.

This is a proof of concept: sessions live in memory and there are no accounts.

📖 **I wrote about how and why I built this:
[vickychappuis.dev/projects/raparena](https://vickychappuis.dev/projects/raparena)**

## Running locally

The quickest path is Docker Compose:

```bash
cp .env.example .env   # then fill in OPENAI_API_KEY and ELEVENLABS_API_KEY
docker compose up
```

- Frontend: http://localhost:5173
- API: http://localhost:8000 (docs at `/docs`)

Without Docker you need Python 3.12+ and Node 22+:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

`OPENAI_API_KEY` and `ELEVENLABS_API_KEY` are required; everything else has
sensible defaults (see the comments in `.env.example`). Set
`MOCK_ELEVENLABS=true` with a `MOCK_RESPONSE_PATH` to develop without spending
ElevenLabs credits. Missing keys don't stop the server — it starts, logs which
ones are absent, and battles just fail until you set them.

## Layout

```
frontend/   React + TypeScript + Vite (Web Audio, mic recording)
api/        FastAPI web layer — routes, pipeline orchestration
core/       Domain logic: lyricist agent, beat grid, STT, prompts
assets/     Base instrumentals (*_<bpm>bpm.mp3 — tempo parsed from the name)
tests/      Backend suite (external APIs stubbed)
```

## Tests & checks

```bash
pip install -r requirements-dev.txt
ruff check . && mypy && python -m pytest

cd frontend && npm run lint && npm test && npm run build
```

The backend suite drives real battles over the real HTTP API and background
pipeline, stubbing only the three external boundaries. It costs nothing to run
and needs no API keys. CI runs all of the above on every push.

## Limits

This is a POC and the guard rails are deliberately blunt: sessions live in
memory (a restart drops every battle in progress), the rate limit (4/hour,
15/day) is **global rather than per-user** — a spend cap on the API keys, not
abuse protection — there is no authentication, and nothing moderates what
either side says.

## Deploying your own copy

If you fork this, **change the backend URL in `frontend/vercel.json`** — its
`/api` and `/static` rewrites point at this project's own backend, so left as
they are your deployment sends its traffic (and its bill) there, and shares
this deployment's rate limit. The API needs `OPENAI_API_KEY`,
`ELEVENLABS_API_KEY`, and `ALLOWED_ORIGINS` set to your frontend's origin;
`api/Dockerfile` builds it from the repo root.

## License

All rights reserved — see [LICENSE](LICENSE). The source is public so you can
read it; that grants no right to use, copy, modify, or redistribute it. Get in
touch if you want to do any of those.

The bundled assets are covered too: the base instrumental (`assets/tracks/`)
and the artwork (`frontend/public/`) are used under licences held by the author
and cannot be redistributed.
