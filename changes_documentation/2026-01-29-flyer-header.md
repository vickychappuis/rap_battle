# 2026-01-29 – Flyer header added to web UI

- Added `FlyerHeader` component (neo-deco SVG frame) to the battle page so the app opens with the provided decorative border.
- Styled header for responsiveness (mobile-to-desktop) and aligned with the visual style guide palette/typography.
- Integrated header into `BattleStage` so it appears above the session controls and status.
- Expanded page width and tied spacing to a responsive `--page-padding` token so the header and layout fill desktop viewport without feeling cramped.
