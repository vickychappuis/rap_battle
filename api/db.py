"""Database connection and table initialization for Postgres (Supabase)."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_tables():
    """Create tables if they don't exist."""
    if not DATABASE_URL:
        print("[db] DATABASE_URL not set, skipping table init")
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS credits (
                        code TEXT PRIMARY KEY,
                        remaining INTEGER NOT NULL DEFAULT 2,
                        contact TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS access_requests (
                        id SERIAL PRIMARY KEY,
                        contact TEXT NOT NULL,
                        code TEXT,
                        requested_at TIMESTAMP DEFAULT NOW()
                    );
                """)
            conn.commit()
        print("[db] Tables initialized")
    except Exception as e:
        print(f"[db] Warning: could not init tables: {e}")
