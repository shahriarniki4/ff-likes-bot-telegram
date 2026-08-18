import httpx
import asyncio
import json
import time
from dataclasses import dataclass
from get_jwt import create_jwt
from encrypt_like_body import create_like_payload
from count_likes import (
    PlayerSnapshot,
    get_base_url,
    get_player_snapshot,
    normalize_server_url,
)
from storage import GuestDataError, load_guests, load_usage
from storage import save_usage as persist_usage

VERIFY_POLL_ATTEMPTS = 6
VERIFY_POLL_INTERVAL_SECONDS = 1

usage_by_target = load_usage()


@dataclass(frozen=True)
class ApiFailure:
    guest_uid: str
    status_code: int | None
    response: str


@dataclass(frozen=True)
class LikeAttempt:
    guest_uid: str
    failure: ApiFailure | None = None


@dataclass(frozen=True)
class LikeSendResult:
    player: PlayerSnapshot
    before: int
    after: int
    planned: int
    attempts: tuple[LikeAttempt, ...]
    verification_error: str | None = None

    @property
    def sent_amount(self) -> int:
        return max(0, self.after - self.before)

    @property
    def api_failures(self) -> tuple[ApiFailure, ...]:
        return tuple(
            attempt.failure
            for attempt in self.attempts
            if attempt.failure is not None
        )


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
    persist_usage(usage_by_target)

async def like_with_guest(
    guest: dict,
    target_uid: str,
    base_url: str,
    semaphore: asyncio.Semaphore,
) -> LikeAttempt:
    guest_uid = str(guest.get("uid", "0"))
    guest_pass = guest.get("password", "")

    if guest_used_for_target(target_uid, guest_uid):
        return LikeAttempt(
            guest_uid,
            ApiFailure(
                guest_uid,
                None,
                f"Guest account is already used for target {target_uid}.",
            ),
        )

    async with semaphore:
        try:
            jwt, region, server_url_from_jwt = await create_jwt(guest_uid, guest_pass)
            # BD accounts use the India client gateway. The login response is
            # authoritative when it supplies a region; otherwise use the
            # region selected by the user.
            request_region = (region or "IND").strip().upper()
            if request_region == "BD":
                request_region = "IND"
            payload = create_like_payload(int(target_uid), request_region)
            
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

            like_base_url = normalize_server_url(server_url_from_jwt, request_region)
            async with httpx.AsyncClient(timeout=30) as client:
                url = f"{like_base_url}/LikeProfile"
                response = await client.post(url, data=payload, headers=headers, timeout=30)

            response_text = response.text.strip()
            if not 200 <= response.status_code < 300:
                failure = ApiFailure(
                    guest_uid,
                    response.status_code,
                    response_text[:500] or "Empty response body.",
                )
                print(
                    f"[{guest_uid}] Like API failed with HTTP "
                    f"{response.status_code}: {failure.response}"
                )
                return LikeAttempt(guest_uid, failure)

            # A 2xx response only means the request reached the endpoint. Some
            # API responses explicitly report a rejected like even with HTTP
            # 200, so preserve that failure for the final bot response.
            api_failure = _extract_api_failure(
                guest_uid,
                response.status_code,
                response_text,
            )
            if api_failure is not None:
                print(f"[{guest_uid}] Like API rejected the request: {api_failure.response}")
                return LikeAttempt(guest_uid, api_failure)

            print(
                f"[{guest_uid}] Like request accepted by API with HTTP "
                f"{response.status_code}; waiting for live count verification."
            )
            return LikeAttempt(guest_uid)

        except Exception as e:
            failure = ApiFailure(guest_uid, None, str(e)[:500])
            print(f"[{guest_uid}] Like request failed: {failure.response}")
            return LikeAttempt(guest_uid, failure)


def _extract_api_failure(
    guest_uid: str,
    status_code: int,
    response_text: str,
) -> ApiFailure | None:
    if not response_text:
        return None

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    for key in ("success", "ok"):
        value = payload.get(key)
        if (
            value is False
            or (isinstance(value, (int, float)) and value == 0)
            or (
                isinstance(value, str)
                and value.strip().lower() in {"false", "0", "failed", "error"}
            )
        ):
            return ApiFailure(guest_uid, status_code, response_text[:500])

    status_value = payload.get("status")
    if (
        status_value == 0
        or (
            isinstance(status_value, str)
            and status_value.strip().lower()
            in {"failed", "failure", "error", "rejected", "false", "0"}
        )
    ):
        return ApiFailure(guest_uid, status_code, response_text[:500])

    for key in ("error", "errors", "failure"):
        if payload.get(key):
            return ApiFailure(guest_uid, status_code, response_text[:500])

    return None


async def _verify_after_snapshot(
    uid: str,
    token: str,
    region: str,
    base_url: str,
    before: PlayerSnapshot,
) -> tuple[PlayerSnapshot, str | None]:
    """Allow the live profile a few seconds to reflect accepted likes."""
    last_snapshot = before
    last_error: str | None = None

    for attempt_number in range(VERIFY_POLL_ATTEMPTS):
        try:
            last_snapshot = await get_player_snapshot(
                uid,
                token,
                region,
                base_url=base_url,
            )
            last_error = None
            if last_snapshot.likes > before.likes:
                return last_snapshot, None
        except Exception as exc:
            last_error = str(exc)

        if attempt_number < VERIFY_POLL_ATTEMPTS - 1:
            await asyncio.sleep(VERIFY_POLL_INTERVAL_SECONDS)

    return last_snapshot, last_error


async def send_likes(
    uid_to_like: str,
    server_name: str,
    requested_likes: int,
    max_concurrency: int,
) -> LikeSendResult:
    if not uid_to_like.isdigit():
        raise ValueError("Target UID must contain digits only.")
    if not 1 <= requested_likes <= 100:
        raise ValueError("Like count must be between 1 and 100.")
    if not 1 <= max_concurrency <= 50:
        raise ValueError("Concurrency must be between 1 and 50.")

    try:
        guests = load_guests()
    except GuestDataError as exc:
        raise RuntimeError(str(exc)) from exc

    print(f"\n{len(guests)} guest accounts found")
    semaphore = asyncio.Semaphore(max_concurrency)
    base_url = get_base_url(server_name)

    if not guests:
        raise RuntimeError(
            "No guest accounts configured. Set GUESTS_JSON in the hosting "
            "environment or add guests_manager/guests_converted.json."
        )

    available_guests = [
        g
        for g in guests
        if not guest_used_for_target(uid_to_like, str(g.get("uid", "0")))
    ]

    if not available_guests:
        print(f"No available guests left for target {uid_to_like}")
        save_usage()
        raise RuntimeError(f"No unused guest accounts remain for target {uid_to_like}.")

    likes_planned = min(max(0, requested_likes), len(available_guests))
    print(f"Planning to send {likes_planned} likes to {uid_to_like}")

    # This is the authoritative preflight. If the live profile cannot be
    # fetched, do not send requests that cannot later be verified.
    verification_guest = available_guests[0]
    verification_uid = str(verification_guest.get("uid", "0"))
    verification_password = verification_guest.get("password", "")
    verification_jwt, login_region, server_url_from_jwt = await create_jwt(
        verification_uid,
        verification_password,
    )
    verification_region = (login_region or server_name).strip().upper()
    verification_base_url = normalize_server_url(
        server_url_from_jwt,
        verification_region,
    )
    before_snapshot = await get_player_snapshot(
        uid_to_like,
        verification_jwt,
        verification_region,
        base_url=verification_base_url or base_url,
    )

    tasks = []
    for g in available_guests[:likes_planned]:
        tasks.append(like_with_guest(g, uid_to_like, base_url, semaphore))

    attempts = tuple(await asyncio.gather(*tasks))

    # Never infer delivery from an HTTP status. Fetch the real profile again
    # after the whole batch and calculate the exact change.
    after_snapshot, verification_error = await _verify_after_snapshot(
        uid_to_like,
        verification_jwt,
        verification_region,
        verification_base_url or base_url,
        before_snapshot,
    )

    sent_amount = max(0, after_snapshot.likes - before_snapshot.likes)
    if sent_amount > 0:
        # A count increase is the only evidence used for the user-facing
        # result. Mark at most that many clean attempts as used so a batch that
        # produced no real change can be retried instead of being exhausted.
        remaining_to_mark = sent_amount
        timestamp = int(time.time() * 1000)
        for attempt in attempts:
            if remaining_to_mark <= 0:
                break
            if attempt.failure is None:
                mark_used(uid_to_like, attempt.guest_uid, timestamp)
                remaining_to_mark -= 1
        save_usage()

    print(
        f"\nCompleted. Verified likes added: {sent_amount}; "
        f"requested: {likes_planned}"
    )
    return LikeSendResult(
        player=after_snapshot,
        before=before_snapshot.likes,
        after=after_snapshot.likes,
        planned=likes_planned,
        attempts=attempts,
        verification_error=verification_error,
    )

async def main():
    uid_to_like = input("Enter UID to like: ").strip()
    server_name = input("Enter server name (e.g., IND, BR, US): ").strip().upper()
    requested_likes = int(input("How many likes do you want to send? (1-100): "))
    max_concurrency = int(input("Concurrent requests? (1-50): "))
    await send_likes(uid_to_like, server_name, requested_likes, max_concurrency)

if __name__ == "__main__":
    asyncio.run(main())
