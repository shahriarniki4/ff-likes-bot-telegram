import json
from pathlib import Path


GUESTS_FILE = Path(__file__).resolve().parent / "guests_converted.json"


def count() -> int:
    """Return the number of locally stored guest accounts."""
    if not GUESTS_FILE.exists():
        return 0

    try:
        with GUESTS_FILE.open("r", encoding="utf-8") as f:
            guests = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Guest account data is not valid JSON: {GUESTS_FILE}") from exc

    if not isinstance(guests, list):
        raise ValueError(f"Guest account data must be a JSON list: {GUESTS_FILE}")

    return len(guests)

if __name__ == "__main__":
    guest_count = count()
    print(f"Total guest accounts: {guest_count}")
