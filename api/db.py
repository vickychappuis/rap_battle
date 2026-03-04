"""Database connection and table initialization for Postgres (Supabase)."""

import os
import socket
from urllib.parse import urlparse, urlunparse
import psycopg2
from psycopg2.extras import RealDictCursor


def _force_ipv4(url: str) -> str:
    """Replace the hostname with its IPv4 address to avoid IPv6 issues."""
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    try:
        ipv4 = socket.getaddrinfo(parsed.hostname, None, socket.AF_INET)[0][4][0]
        netloc = f"{parsed.username}:{parsed.password}@{ipv4}" if parsed.username else ipv4
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    except (socket.gaierror, IndexError):
        return url


DATABASE_URL = _force_ipv4(os.environ.get("DATABASE_URL", ""))


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
