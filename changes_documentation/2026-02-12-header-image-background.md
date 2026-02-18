# 2026-02-12 – Header image background update

- Replaced the flat `FlyerHeader` rectangle background with the provided `frontend/public/header.png` asset.
- Kept existing header layout, logo placement, and responsive sizing unchanged to avoid layout regressions.
- Implemented the change in `frontend/src/styles/global.css` using a centered, non-repeating `cover` background image.
- Updated header image positioning to `center bottom` and increased header height via `clamp(...)` so the torn-paper lower edge remains visible across viewports.
- Refined the approach to keep header height compact while preserving the torn edge by adding a `::after` torn overlay that extends below the header and sits above the following section.
