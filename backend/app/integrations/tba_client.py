# backend/app/integrations/tba_client.py
import logging
import time
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://www.thebluealliance.com/api/v3"

_etag_cache: dict[str, tuple[str, dict | list]] = {}


def _headers(path: str) -> dict:
    h = {"X-TBA-Auth-Key": settings.TBA_API_KEY}
    if path in _etag_cache:
        h["If-None-Match"] = _etag_cache[path][0]
    return h


def _get(path: str) -> dict | list | None:
    url = f"{BASE_URL}{path}"

    if not settings.TBA_API_KEY:
        raise RuntimeError("TBA_API_KEY is not set in your backend/.env file")

    for attempt in range(3):
        try:
            r = httpx.get(url, headers=_headers(path), timeout=15)
        except httpx.ConnectError:
            raise RuntimeError("Cannot reach thebluealliance.com — check your internet connection")
        except httpx.TimeoutException:
            raise RuntimeError("TBA request timed out")

        logger.debug("TBA %s → %d", path, r.status_code)

        if r.status_code == 304:
            return _etag_cache[path][1]

        if r.status_code == 401:
            raise RuntimeError(
                f"TBA rejected the API key (401). "
                f"Key used: '{settings.TBA_API_KEY[:6]}…' — "
                f"check TBA_API_KEY in backend/.env"
            )

        if r.status_code == 429:
            wait = 2 ** attempt
            logger.warning("TBA rate limited, retrying in %ds", wait)
            time.sleep(wait)
            continue

        if r.status_code == 404:
            raise ValueError(f"TBA returned 404 for {path}")

        if not r.is_success:
            raise RuntimeError(f"TBA returned {r.status_code} for {path}: {r.text[:200]}")

        data = r.json()
        etag = r.headers.get("ETag", "")
        if etag:
            _etag_cache[path] = (etag, data)

        return data

    raise RuntimeError(f"TBA rate limit exceeded after 3 retries: {path}")


def check_api_key() -> dict:
    """Test the API key by hitting a lightweight TBA endpoint. Returns status dict."""
    if not settings.TBA_API_KEY:
        return {"ok": False, "reason": "TBA_API_KEY is not set in backend/.env"}
    try:
        result = _get("/status")
        return {"ok": True, "tba_status": result}
    except RuntimeError as e:
        return {"ok": False, "reason": str(e)}


def get_event(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}")

def get_event_teams(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}/teams")

def get_event_matches(event_key: str) -> dict | list | None:
    return _get(f"/event/{event_key}/matches")

def get_events_by_year(year: int) -> dict | list | None:
    return _get(f"/events/{year}")

def get_teams_page(page: int = 0) -> dict | list | None:
    """Fetch a page of all registered teams from TBA (500 per page)."""
    return _get(f"/teams/{page}")