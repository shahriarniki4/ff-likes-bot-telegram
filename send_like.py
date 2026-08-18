import httpx
import asyncio
import binascii
import json
import os
import time
from pathlib import Path
from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from guests_manager.count_guest import count

PROJECT_ROOT = Path(__file__).resolve().parent
guests_file = PROJECT_ROOT / "guests_manager" / "guests_converted.json"
usage_dir = PROJECT_ROOT / "usage_history"
usage_file = usage_dir / "guest_usage_by_target.json"

os.makedirs(usage_dir, exist_ok=True)

if os.path.exists(usage_file):
    with usage_file.open("r", encoding="utf-8") as f:
        usage_by_target = json.load(f)
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
    with usage_file.open("w", encoding="utf-8") as f:
        json.dump(usage_by_target, f, indent=2)

def get_base_url(server_name: str) -> str:
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ggblueshark.com"

async def like_with_guest(guest: dict, target_uid: str, BASE_URL: str, semaphore: asyncio.Semaphore) -> bool:
    guest_uid = str(guest.get("uid", "0"))
    guest_pass = guest.get("password", "")
    now_ms = int(time.time() * 1000)

    if guest_used_for_target(target_uid, guest_uid):
        print(f"[{guest_uid}] Permanently used for target {target_uid}, skipping...")
        return False

    async with semaphore:
        try:
            jwt, region, server_url_from_jwt = await create_jwt(guest_uid, guest_pass)
            payload = create_like_payload(int(target_uid), region)
            
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
                url = f"{BASE_URL}/LikeProfile"
                response = await client.post(url, data=payload, headers=headers, timeout=30)
                response.raise_for_status()

            print(f"[{guest_uid}] Like sent to {target_uid}! Status: {response.status_code}")
            mark_used(target_uid, guest_uid, now_ms)
            return True

        except Exception as e:
            print(f"[{guest_uid}] Error: {str(e)}")

    return False

async def main():
    uid_to_like = input("Enter UID to like: ").strip()
    server_name_in = input("Enter server name (e.g., IND, BR, US): ").strip().upper()

    guest_count_val = count()
    print(f"\n{guest_count_val} guest accounts found")

    requested_likes_in = input("How many likes you want to send? (default: 100): ").strip()
    requested_likes = int(requested_likes_in) if requested_likes_in else 100

    max_conc_in = input("Requests per second? (default: 20): ").strip()
    MAX_CONCURRENT = int(max_conc_in) if max_conc_in else 20
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    BASE_URL = get_base_url(server_name_in)

    ensure_target(uid_to_like)
    
    if not os.path.exists(guests_file):
        print(f"No guests file found at {guests_file}")
        save_usage()
        return

    with guests_file.open("r", encoding="utf-8") as f:
        guests = json.load(f)

    available_guests = [g for g in guests if not guest_used_for_target(uid_to_like, str(g.get("uid", "0")))]

    if not available_guests:
        print(f"No available guests left for target {uid_to_like}")
        save_usage()
        return

    likes_planned = min(max(0, requested_likes), len(available_guests))
    print(f"Planning to send {likes_planned} likes to {uid_to_like}")

    tasks = []
    for g in available_guests[:likes_planned]:
        tasks.append(like_with_guest(g, uid_to_like, BASE_URL, semaphore))

    results = await asyncio.gather(*tasks)
    save_usage()

    success = sum(1 for r in results if r)
    print(f"\nCompleted. Success: {success}/{likes_planned}")

if __name__ == "__main__":
    asyncio.run(main())
