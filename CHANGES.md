# Multi-Turn Rap Battle

## What Changed

Battles now support multiple rounds (default: 2 rounds per player, 16 bars each).

## Config

```bash
# .env
BARS_PER_TURN=16      # Bars per turn (replaces SECONDS_LENGTH_OF_ANSWER)
TURNS_PER_PLAYER=2    # Rounds per side
BPM=90
```

## New Features

- **Battle History**: Scrolling timeline shows all exchanges
- **Turn Context**: AI references previous rounds in responses
- **Retry Logic**: Failed turns can be retried (up to 2 attempts)
- **Round Indicator**: UI shows current round progress

## Files Modified

| Area | Files |
|------|-------|
| Config | `.env.example` |
| Prompts | `prompts/lyricist_prompt.py` |
| Backend | `api/models/session.py`, `api/services/pipeline.py`, `api/routes/session.py` |
| Frontend | `src/api/session.ts`, `src/hooks/useSession.ts`, `src/components/*.tsx` |

## New Endpoint

```
POST /api/session/{id}/retry  # Retry failed turn
```
