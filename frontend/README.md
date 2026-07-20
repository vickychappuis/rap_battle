# Rap Battle AI — Frontend

React + TypeScript + Vite client for the Rap Battle AI app. It records the
user's bars, drives the battle session against the API, and handles playback:
looping the base instrumental and scheduling the AI response on the beat via the
Web Audio API.

See the [project README](../README.md) for the full picture and how to run
everything with Docker Compose.

## Development

```bash
npm install
npm run dev      # Vite dev server on http://localhost:5173
```

The dev server proxies `/api` and `/static` to the backend. Override the target
with `VITE_API_URL` (defaults to `http://localhost:8000`).

## Scripts

- `npm run dev` — start the dev server
- `npm run build` — type-check and build for production
- `npm run preview` — preview the production build
- `npm run lint` — run ESLint

## Layout

- `src/components/` — UI components
- `src/hooks/` — session and audio-engine hooks
- `src/audio/` — Web Audio engine, beat tracking, mic recorder
- `src/api/` — API client
- `src/data/` — opponent roster
