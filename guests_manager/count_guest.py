import json
from pathlib import Path


GUESTS_FILE = Path(__file__).resolve().parent / "guests_converted.json"

def count():
    """
    Count the number of guest accounts in guests_converted.json
    """
    if not GUESTS_FILE.exists():
        return 0

    with GUESTS_FILE.open("r", encoding="utf-8") as f:
        guests = json.load(f)

    if not isinstance(guests, list):
        raise ValueError(f"Expected a list of accounts in {GUESTS_FILE}")

    return len(guests)

if __name__ == "__main__":
    guest_count = count()
    print(f"Total guest accounts: {guest_count}")
