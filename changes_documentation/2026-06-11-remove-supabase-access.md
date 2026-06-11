# Remove Supabase access system

## Summary

- Removed the unused Supabase/Postgres connection and table initialization.
- Removed invite-code, access-request, and credit API endpoints.
- Removed the unused no-credits UI and access-related routes/styles.
- Updated the landing CTA to open the battle directly.
- Removed `psycopg2-binary` from Python dependencies.

## Behavior

Battle sessions continue to use the existing in-memory global rate limit of four
sessions per hour and fifteen sessions per day. This limit does not depend on
Supabase and resets when the API process restarts.
