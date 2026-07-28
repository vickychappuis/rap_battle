"""The opponent persona: caps, sanitising, and the delimited data block.

The persona is a character sheet for the AI MC (name / age / claims / reality
/ extra_info). It arrives in the body of `POST /api/session`, which accepts
any JSON from anyone — the frontend's OPPONENTS list constrains nothing about
what the server actually receives. So every value here is **untrusted text
that ends up inside an LLM prompt** and is treated accordingly:

1. Raw length is capped per field (the API rejects oversized input with a 422).
2. The text is normalised, stripped of control/format codepoints, and stripped
   of anything shaped like prompt structure.
3. It is rendered inside explicit markers so the surrounding instructions can
   frame it as data describing a character, never as instructions to follow.

Steps 2 and 3 live here (rather than only in the pydantic model) so that any
caller reaching the prompt builders directly gets the same treatment.
"""

import re
import unicodedata
from typing import Mapping, Optional

# Per-field caps, applied to the RAW client value. Generous enough for the
# comedy one-liners the game actually sends, small enough that a persona can
# never dwarf the prompt it sits in.
PERSONA_FIELD_LIMITS = {
    "name": 60,
    "claims": 200,
    "reality": 200,
    "extra_info": 300,
}

# Cap on the whole block. Deliberately below the sum of the per-field caps
# (760), so filling every field to its own limit still gets rejected.
MAX_PERSONA_BLOCK_CHARS = 700

MIN_AGE = 1
MAX_AGE = 120

# The order fields are rendered in, and the only keys ever read from a persona
# mapping — anything else the client sends (id, imageSrc, ...) is ignored.
PERSONA_FIELD_ORDER = ("name", "age", "claims", "reality", "extra_info")

# Codepoint categories dropped outright: control (Cc), format (Cf — zero-width
# joiners, bidi overrides), surrogates (Cs) and private use (Co). These are the
# characters that let text hide from a human reviewer while the model still
# reads it.
_DROPPED_CATEGORIES = {"Cc", "Cf", "Cs", "Co"}

# Anything shaped like prompt structure: our own markers, code fences, chat
# template markers, markdown headings and horizontal rules.
_STRUCTURE_RE = re.compile(r"[`<>{}|#\\]|-{3,}|={3,}|_{3,}")

_WHITESPACE_RE = re.compile(r"\s+")

PERSONA_OPEN = "<<<OPPONENT_PERSONA>>>"
PERSONA_CLOSE = "<<<END_OPPONENT_PERSONA>>>"


def sanitize_prompt_text(value: str, max_chars: int) -> str:
    """Reduce untrusted text to a single harmless line of prompt content.

    Normalises lookalikes, drops invisible codepoints, removes prompt-structure
    characters, collapses whitespace and truncates. Truncation here is a
    backstop: the API rejects over-length input before it gets this far.
    """
    text = unicodedata.normalize("NFKC", str(value))
    # Newlines/tabs become spaces (they are Cc, but losing the word boundary
    # would silently glue words together); every other Cc/Cf/Cs/Co is dropped.
    text = "".join(
        " "
        if char in "\n\r\t"
        else ("" if unicodedata.category(char) in _DROPPED_CATEGORIES else char)
        for char in text
    )
    text = _STRUCTURE_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()[:max_chars]


def build_persona_data_block(persona: Optional[Mapping]) -> Optional[str]:
    """Render a persona mapping as a delimited, sanitised `key: value` block.

    Returns None when there is nothing usable to render, so callers can fall
    back to their own no-persona wording. Callers are responsible for the
    instructions that frame this block as untrusted data.
    """
    if not persona:
        return None

    lines = []
    for field in PERSONA_FIELD_ORDER:
        value = persona.get(field)
        if value is None or value == "":
            continue
        if field == "age":
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if not MIN_AGE <= value <= MAX_AGE:
                continue
            lines.append(f"age: {value}")
            continue
        cleaned = sanitize_prompt_text(str(value), PERSONA_FIELD_LIMITS[field])
        if cleaned:
            lines.append(f"{field}: {cleaned}")

    if not lines:
        return None

    body = "\n".join(lines)[:MAX_PERSONA_BLOCK_CHARS]
    return f"{PERSONA_OPEN}\n{body}\n{PERSONA_CLOSE}"
