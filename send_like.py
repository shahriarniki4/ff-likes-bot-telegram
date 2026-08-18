import httpx
import asyncio
import json
import time
from pathlib import Path
from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from guests_manager.count_guest import count

PROJECT_ROOT = Path(__file__).resolve().parent
GUESTS_FILE = PROJECT_ROOT / "guests_manager" / "guests_converted.json"
USAGE_DIR = PROJECT_ROOT / "usage_history"
USAGE_FILE = USAGE_DIR / "guest_usage_by_target.json"

USAGE_DIR.mkdir(exist_ok=True)

if USAGE_FILE.exists():
    try:
        with USAGE_FILE.open("r", encoding="utf-8") as f:
            usage_by_target = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Usage history is not valid JSON: {USAGE_FILE}") from exc
else:
    usage_by_target = {}

def ensure_target(target_uid: str):
    if target_uid not in usage_by_target:
        usage_by_target[target_uid] = {"used_guests": {}, "total_likes": 0}

def guest_used_for_target(target_uid: str, guest_uid: str) -> bool:
    ensure_target(target_uid)
    return guest_uid in usage_by_target[target_uid]["used_guests"]

def mark_used(target_uid: str, guest_uid: str, ts_ms: int):
    ensure_target(target_uid)
    usage_by_target[target_uid]["used_guests"][guest_uid] = ts_ms
    usage_by_target[target_uid]["total_likes"] = len(usage_by_target[target_uid]["used_guests"])

def save_usage():
    with USAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(usage_by_target, f, indent=2)

def get_base_url(server_name: str) -> str:
    # Bangladesh traffic uses the India gateway; there is no separate
    # client.bd.freefiremobile.com endpoint.
    if server_name in {"BD", "IND"}:
        return "https://client.ind.freefiremobile.com"
    elif server_name in {"BR", "US", "SA", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ggblueshark.com"

async def like_with_guest(
    guest: dict,
    target_uid: str,
    base_url: str,
    semaphore: asyncio.Semaphore,
) -> bool:
    guest_uid = str(guest.get("uid", "0"))
    guest_pass = guest.get("password", "")
    now_ms = int(time.time() * 1000)

    if guest_used_for_target(target_uid, guest_uid):
        print(f"[{guest_uid}] Permanently used for target {target_uid}, skipping...")
        return False

    async with semaphore:
        try:
            jwt, region, server_url_from_jwt = await create_jwt(guest_uid, guest_pass)
            payload = create_like_payload(int(target_uid), region or "IND")
            
            headers = {
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Build/UP1A.231005.007)",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/octet-stream",
                "Authorization": f"Bearer {jwt}",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": "OB50",
            }

            async with httpx.AsyncClient() as client:
                url = f"{(server_url_from_jwt or base_url).rstrip('/')}/LikeProfile"
                response = await client.post(url, data=payload, headers=headers, timeout=30)
                response.raise_for_status()

            print(f"[{guest_uid}] Like sent to {target_uid}! Status: {response.status_code}")
            mark_used(target_uid, guest_uid, now_ms)
            return True

        except Exception as e:
            print(f"[{guest_uid}] Error: {str(e)}")

    return False

async def send_likes(
    uid_to_like: str,
    server_name: str,
    requested_likes: int,
    max_concurrency: int,
) -> tuple[int, int]:
    if not uid_to_like.isdigit():
        raise ValueError("Target UID must contain digits only.")
    if not 1 <= requested_likes <= 100:
        raise ValueError("Like count must be between 1 and 100.")
    if not 1 <= max_concurrency <= 50:
        raise ValueError("Concurrency must be between 1 and 50.")

    guest_count_val = count()
    print(f"\n{guest_count_val} guest accounts found")
    semaphore = asyncio.Semaphore(max_concurrency)
    base_url = get_base_url(server_name)

    ensure_target(uid_to_like)
    
    if not GUESTS_FILE.exists():
        raise RuntimeError(
            "No guest accounts found. Add guests_manager/guests_converted.json "
            "before sending likes."
        )

    with GUESTS_FILE.open("r", encoding="utf-8") as f:
        try:
            guests = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Guest account data is not valid JSON: {GUESTS_FILE}") from exc

    if not isinstance(guests, list):
        raise ValueError(f"Guest account data must be a JSON list: {GUESTS_FILE}")

    available_guests = [g for g in guests if not guest_used_for_target(uid_to_like, str(g.get("uid", "0")))]

    if not available_guests:
        print(f"No available guests left for target {uid_to_like}")
        save_usage()
        return 0, 0

    likes_planned = min(max(0, requested_likes), len(available_guests))
    print(f"Planning to send {likes_planned} likes to {uid_to_like}")

    tasks = []
    for g in available_guests[:likes_planned]:
        tasks.append(like_with_guest(g, uid_to_like, base_url, semaphore))

    results = await asyncio.gather(*tasks)
    save_usage()

    success = sum(1 for r in results if r)
    print(f"\nCompleted. Success: {success}/{likes_planned}")
    return success, likes_planned

async def main():
    uid_to_like = input("Enter UID to like: ").strip()
    server_name = input("Enter server name (e.g., IND, BR, US): ").strip().upper()
    requested_likes = int(input("How many likes do you want to send? (1-100): "))
    max_concurrency = int(input("Concurrent requests? (1-50): "))
    await send_likes(uid_to_like, server_name, requested_likes, max_concurrency)

if __name__ == "__main__":
    asyncio.run(main())
