# Guest manager module
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from storage import count_guests  # noqa: E402


def count() -> int:
    """Return the number of configured guest accounts."""
    return count_guests()


if __name__ == "__main__":
    print(f"Total guest accounts: {count()}")
