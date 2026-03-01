"""Access validation routes for the rap battle API."""

import os
import re
import secrets
import string
from datetime import datetime, date

import requests as http_requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from api.db import get_conn

router = APIRouter(prefix="/api/access", tags=["access"])

INVITE_CODES: set[str] = set(
    code.strip()
    for code in os.environ.get("INVITE_CODES", "").split(",")
    if code.strip()
)

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_REQUESTS_PER_DAY = 5
INITIAL_CREDITS = 2


# --- DB helpers ---

def _use_credit(code: str) -> bool:
    """Decrement credit. Returns True if allowed (has credits or legacy unlimited code)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT remaining FROM credits WHERE code = %s", (code,))
            row = cur.fetchone()
            if not row:
                return True  # legacy code without credit tracking
            if row[0] <= 0:
                return False
            cur.execute(
                "UPDATE credits SET remaining = remaining - 1 WHERE code = %s",
                (code,),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def _get_remaining_credits(code: str) -> int:
    """Returns remaining credits, or -1 if code has no credit tracking (unlimited)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT remaining FROM credits WHERE code = %s", (code,))
            row = cur.fetchone()
            if not row:
                return -1
            return row[0]
    finally:
        conn.close()


def _save_credit(code: str, contact: str) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO credits (code, remaining, contact) VALUES (%s, %s, %s)",
                (code, INITIAL_CREDITS, contact),
            )
        conn.commit()
    finally:
        conn.close()


def _save_request(contact: str, code: str) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO access_requests (contact, code) VALUES (%s, %s)",
                (contact, code),
            )
        conn.commit()
    finally:
        conn.close()


def _count_requests_today() -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM access_requests WHERE requested_at::date = CURRENT_DATE"
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def _load_requests() -> list:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT contact, code, requested_at FROM access_requests ORDER BY requested_at"
            )
            return [
                {"contact": r[0], "code": r[1], "requested_at": r[2].isoformat() if r[2] else None}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


# --- Email helpers ---

def _send_invite_email(email: str, code: str) -> None:
    if not RESEND_API_KEY:
        return
    try:
        http_requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "Rap Battle <onboarding@resend.dev>",
                "to": [email],
                "subject": "Your Rap Battle invite code",
                "text": (
                    f"You're in!\n\n"
                    f"Your invite code: {code}\n"
                    f"You have {INITIAL_CREDITS} battle credits.\n\n"
                    f"Head over and start battling!"
                ),
            },
            timeout=5,
        )
    except Exception:
        pass


def _notify_admin(contact: str, code: str) -> None:
    if not RESEND_API_KEY or not NOTIFY_EMAIL:
        return
    try:
        http_requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "Rap Battle <onboarding@resend.dev>",
                "to": [NOTIFY_EMAIL],
                "subject": "New access request — code auto-sent",
                "text": (
                    f"Someone requested access and got an auto-invite.\n\n"
                    f"Contact: {contact}\n"
                    f"Code: {code}\n"
                    f"Credits: {INITIAL_CREDITS}\n"
                    f"Time: {datetime.utcnow().isoformat()}"
                ),
            },
            timeout=5,
        )
    except Exception:
        pass


# --- Utilities ---

def is_valid_invite_code(code: str) -> bool:
    """Check if an invite code is in the allowed list."""
    return code.strip() in INVITE_CODES


def _generate_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part = lambda: "".join(secrets.choice(chars) for _ in range(4))
    return f"{part()}-{part()}"


def _check_admin(key: str) -> None:
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden.")


# --- Models ---

class ValidateRequest(BaseModel):
    invite_code: Optional[str] = None


class InviteRequest(BaseModel):
    contact: str


# --- Routes ---

@router.post("/validate")
async def validate(req: ValidateRequest):
    """Validate an invite code. Returns 200 if valid, 401 if not."""
    if not req.invite_code or not is_valid_invite_code(req.invite_code):
        raise HTTPException(status_code=401, detail="Invalid invite code.")
    return {"ok": True}


@router.post("/request")
async def request_invite(req: InviteRequest):
    """Auto-generate invite code, email it to requester, notify admin."""
    contact = req.contact.strip()
    if not contact:
        raise HTTPException(status_code=400, detail="Contact info required.")

    if not EMAIL_RE.match(contact):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if _count_requests_today() >= MAX_REQUESTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many requests today. Try again tomorrow.")

    code = _generate_code()
    INVITE_CODES.add(code)
    _save_credit(code, contact)
    _save_request(contact, code)

    _send_invite_email(contact, code)
    _notify_admin(contact, code)

    return {"ok": True}


@router.get("/credits")
async def get_credits(code: str = Query(...)):
    """Return remaining credits for an invite code."""
    remaining = _get_remaining_credits(code)
    return {"remaining": remaining}


@router.get("/requests")
async def list_requests(key: str = Query(...)):
    """Admin: list all access requests."""
    _check_admin(key)
    return _load_requests()


@router.post("/generate")
async def generate_invite(key: str = Query(...)):
    """Admin: generate a new invite code and add it to the live set."""
    _check_admin(key)
    code = _generate_code()
    INVITE_CODES.add(code)
    return {"code": code}
