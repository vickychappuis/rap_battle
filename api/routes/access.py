"""Access validation routes for the rap battle API."""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/access", tags=["access"])

# Valid invite codes from environment (comma-separated)
INVITE_CODES = set(
    code.strip()
    for code in os.environ.get("INVITE_CODES", "").split(",")
    if code.strip()
)


def is_valid_invite_code(code: str) -> bool:
    """Check if an invite code is in the allowed list."""
    return code.strip() in INVITE_CODES


class ValidateRequest(BaseModel):
    invite_code: Optional[str] = None


@router.post("/validate")
async def validate(req: ValidateRequest):
    """Validate an invite code. Returns 200 if valid, 401 if not."""
    if not req.invite_code or not is_valid_invite_code(req.invite_code):
        raise HTTPException(status_code=401, detail="Invalid invite code.")
    return {"ok": True}
