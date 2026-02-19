# Opponent Dataset Expansion

## Date
2026-02-19

## Summary
Converted opponent profile content from hardcoded component text into a reusable frontend dataset and added two new opponents:
- Bad Panda
- Rat Killai

## Files Changed
- `frontend/src/data/opponents.ts`
- `frontend/src/components/PlayerCard.tsx`
- `frontend/src/components/RecordingSection.tsx`

## Details
- Added `OpponentProfile` type and `OPPONENTS` dataset array with:
  - Max Gorilla (existing profile)
  - Bad Panda (new)
  - Rat Killai (new)
- Updated `PlayerCard` to accept profile data via props.
- Updated `RecordingSection` to select and render one opponent from the dataset (random pick per page load).

## Why
This keeps character content centralized and makes it easier to add/edit opponents without touching presentation markup.
