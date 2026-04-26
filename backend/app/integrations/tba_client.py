# backend/app/integrations/tba_client.py
import time
import httpx
from app.core.config import settings

BASE_URL = "https://www.thebluealliance.com/api/v3"

# ETag cache: path -> (etag, response_data)
# Avoids re-processing unchanged data — TBA returns 304 Not Modified
# when the ETag matches, saving bandwidth and parse time.
_etag_cache: dict[str, tuple[str, dict | list]] = {}


def _headers(path: str) -> dict:
    h = {"X-TBA-Auth-Key": settings.TBA_API_KEY}
    if path in _etag_cache:
        h["If-None-Match"] = _etag_cache[path][0]
    return h


def _get(path: str) -> dict | list | None:
    """
    GET from TBA with ETag caching and retry on 429.

    Returns:
        - Parsed JSON on fresh data (200)
        - None if data is unchanged (304 Not Modified)
        - Raises ValueError on 404
        - Raises RuntimeError on rate limit exhaustion
    """
    url = f"{BASE_URL}{path}"
    for attempt in range(3):
        r = httpx.get(url, headers=_headers(path), timeout=10)

        if r.status_code == 304:
            # Data unchanged since last fetch — return cached value
            return _etag_cache[path][1]

        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue

        if r.status_code == 404:
            raise ValueError(f"TBA returned 404 for {path}")

        r.raise_for_status()

        data = r.json()
        etag = r.headers.get("ETag", "")
        if etag:
            _etag_cache[path] = (etag, data)

        return data

    raise RuntimeError(f"TBA rate limit exceeded after retries: {path}")


def get_event(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}")


def get_event_teams(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}/teams")


def get_event_matches(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}/matches")


def get_events_by_year(year: int) -> dict | list | None:
    return _get(f"/events/{year}")