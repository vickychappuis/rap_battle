"""Access validation routes for the rap battle API."""

import json
import os
import secrets
import string
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/access", tags=["access"])

# Valid invite codes from environment (comma-separated), grows at runtime
INVITE_CODES: set[str] = set(
    code.strip()
    for code in os.environ.get("INVITE_CODES", "").split(",")
    if code.strip()
)

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

REQUESTS_FILE = Path(__file__).parent.parent / "access_requests.json"


def is_valid_invite_code(code: str) -> bool:
    """Check if an invite code is in the allowed list."""
    return code.strip() in INVITE_CODES


def _load_requests() -> list:
    if REQUESTS_FILE.exists():
        return json.loads(REQUESTS_FILE.read_text())
    return []


def _save_requests(requests: list) -> None:
    REQUESTS_FILE.write_text(json.dumps(requests, indent=2))


def _generate_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part = lambda: "".join(secrets.choice(chars) for _ in range(4))
    return f"{part()}-{part()}"


def _check_admin(key: str) -> None:
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden.")


class ValidateRequest(BaseModel):
    invite_code: Optional[str] = None


class InviteRequest(BaseModel):
    contact: str


@router.post("/validate")
async def validate(req: ValidateRequest):
    """Validate an invite code. Returns 200 if valid, 401 if not."""
    if not req.invite_code or not is_valid_invite_code(req.invite_code):
        raise HTTPException(status_code=401, detail="Invalid invite code.")
    return {"ok": True}


@router.post("/request")
async def request_invite(req: InviteRequest):
    """Save an access request (email or handle)."""
    contact = req.contact.strip()
    if not contact:
        raise HTTPException(status_code=400, detail="Contact info required.")

    requests = _load_requests()
    requests.append({
        "contact": contact,
        "requested_at": datetime.utcnow().isoformat(),
    })
    _save_requests(requests)
    return {"ok": True}


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
