from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


REGION_BASE_URLS = {
    # Garena does not expose a separate client.bd endpoint. Bangladesh
    # accounts use the India gateway.
    "BD": "https://client.ind.freefiremobile.com",
    "IND": "https://client.ind.freefiremobile.com",
    "BR": "https://client.us.freefiremobile.com",
    "US": "https://client.us.freefiremobile.com",
    "SA": "https://client.us.freefiremobile.com",
    "SAC": "https://client.us.freefiremobile.com",
    "NA": "https://client.us.freefiremobile.com",
}


class PlayerDataError(RuntimeError):
    """Raised when the live player profile cannot be verified."""


@dataclass(frozen=True)
class PlayerSnapshot:
    uid: str
    name: str
    likes: int
    region: str


def get_base_url(region: str) -> str:
    """Return the live Free Fire gateway for a user-facing region code."""
    normalized_region = region.strip().upper()
    try:
        return REGION_BASE_URLS[normalized_region]
    except KeyError as exc:
        supported = ", ".join(sorted(REGION_BASE_URLS))
        raise ValueError(
            f"Unsupported region {normalized_region!r}. Choose one of: {supported}."
        ) from exc


def normalize_server_url(server_url: str | None, fallback_region: str) -> str:
    """Use the gateway returned by login, falling back to the region mapping."""
    if server_url:
        candidate = server_url.strip().rstrip("/")
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return candidate
    return get_base_url(fallback_region)


def _normalize_key(key: object) -> str:
    return "".join(character for character in str(key).lower() if character.isalnum())


def _find_first_value(payload: Any, aliases: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _normalize_key(key) in aliases:
                return value
        for value in payload.values():
            found = _find_first_value(value, aliases)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_first_value(value, aliases)
            if found is not None:
                return found
    return None


def _parse_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str):
        digits = value.strip()
        if digits.isdigit():
            return int(digits)
    return None


def parse_player_snapshot(
    payload: Any,
    uid: str,
    region: str,
) -> PlayerSnapshot:
    """Extract real profile fields from the live GetPlayerPersonalShow JSON."""
    likes_value = _find_first_value(
        payload,
        {
            "likes",
            "likecount",
            "likescount",
            "totallikes",
            "popularity",
            "popularitycount",
        },
    )
    likes = _parse_non_negative_int(likes_value)
    if likes is None:
        raise PlayerDataError(
            "The player profile response did not include a numeric likes count."
        )

    name_value = _find_first_value(
        payload,
        {"nickname", "playername", "username", "name"},
    )
    name = str(name_value).strip() if name_value is not None else ""
    if not name:
        raise PlayerDataError(
            "The player profile response did not include the player's name."
        )

    return PlayerSnapshot(
        uid=str(uid),
        name=name,
        likes=likes,
        region=region.strip().upper(),
    )


async def GetAccountInformation(
    uid: str,
    token: str,
    server: str,
    endpoint: str,
    base_url: str | None = None,
) -> Any:
    """Fetch a live player endpoint and fail on non-2xx responses."""
    resolved_base_url = normalize_server_url(base_url, server)
    url = f"{resolved_base_url}{endpoint}"
    headers = {
        "User-Agent": (
            "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 "
            "Build/UP1A.231005.007)"
        ),
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                params={"uid": str(uid)},
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise PlayerDataError(f"Player profile request failed: {exc}") from exc

    if not 200 <= response.status_code < 300:
        body = response.text.strip()[:500]
        raise PlayerDataError(
            f"Player profile request failed with HTTP {response.status_code}: {body}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise PlayerDataError(
            "Player profile endpoint returned a non-JSON response."
        ) from exc


async def get_player_snapshot(
    uid: str,
    token: str,
    server: str,
    base_url: str | None = None,
) -> PlayerSnapshot:
    payload = await GetAccountInformation(
        uid,
        token,
        server,
        "/GetPlayerPersonalShow",
        base_url=base_url,
    )
    return parse_player_snapshot(payload, uid, server)


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        snapshot = await get_player_snapshot(
            "123456789",
            "token",
            "IND",
        )
        print(snapshot)

    asyncio.run(main())
