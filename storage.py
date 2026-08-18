"""Runtime data access for guest accounts and usage history.

Hosted deployments (Railway, Render, Koyeb, Fly, Docker, ...) do not ship the
git-ignored runtime files, and their filesystems are usually ephemeral or
read-only. Everything here therefore works from environment variables first and
falls back to local files for development machines.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent

# DATA_DIR lets a host mount a writable volume (for example /data).
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT))).expanduser()

GUESTS_FILE = Path(
    os.getenv("GUESTS_FILE", str(DATA_DIR / "guests_manager" / "guests_converted.json"))
)
USAGE_FILE = Path(
    os.getenv("USAGE_FILE", str(DATA_DIR / "usage_history" / "guest_usage_by_target.json"))
)


class GuestDataError(RuntimeError):
    """Raised when guest account data is missing or malformed."""


def _parse_guests(raw: str, source: str) -> list[dict[str, Any]]:
    try:
        guests = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GuestDataError(f"Guest account data is not valid JSON ({source}).") from exc

    if not isinstance(guests, list):
        raise GuestDataError(f"Guest account data must be a JSON list ({source}).")

    return [guest for guest in guests if isinstance(guest, dict)]


def load_guests() -> list[dict[str, Any]]:
    """Return guest accounts from the environment or the local runtime file."""
    inline = os.getenv("GUESTS_JSON")
    if inline and inline.strip():
        return _parse_guests(inline, "GUESTS_JSON environment variable")

    if GUESTS_FILE.exists():
        return _parse_guests(
            GUESTS_FILE.read_text(encoding="utf-8"),
            str(GUESTS_FILE),
        )

    raise GuestDataError(
        "No guest accounts available. Set GUESTS_JSON in the hosting environment "
        f"or add the file {GUESTS_FILE}."
    )


def count_guests() -> int:
    """Return how many guest accounts are configured (0 when none)."""
    try:
        return len(load_guests())
    except GuestDataError:
        return 0


def load_usage() -> dict[str, Any]:
    if not USAGE_FILE.exists():
        return {}

    try:
        return json.loads(USAGE_FILE.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable history must never stop the bot from starting.
        return {}


def save_usage(usage: dict[str, Any]) -> None:
    """Persist usage history, ignoring read-only/ephemeral hosting filesystems."""
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(usage, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[storage] Could not persist usage history to {USAGE_FILE}: {exc}")
