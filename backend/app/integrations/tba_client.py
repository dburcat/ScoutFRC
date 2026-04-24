# backend/app/integrations/tba_client.py
import time
import httpx
from app.core.config import settings
_API_KEY = settings.TBA_API_KEY

BASE_URL = "https://www.thebluealliance.com/api/v3"

def _headers() -> dict:
    return {"X-TBA-Auth-Key": settings.TBA_API_KEY}

def _get(path: str) -> dict | list:
    """GET from TBA with retry on 429."""
    url = f"{BASE_URL}{path}"
    for attempt in range(3):
        r = httpx.get(url, headers=_headers(), timeout=10)
        if r.status_code == 429:
            time.sleep(2 ** attempt)   # 1s, 2s, 4s
            continue
        if r.status_code == 404:
            raise ValueError(f"TBA returned 404 for {path}")
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TBA rate limit exceeded after retries: {path}")

def get_event(event_key: str) -> dict | list:
    return _get(f"/event/{event_key}")

def get_event_teams(event_key: str) -> dict | list:
    return _get(f"/event/{event_key}/teams")

def get_event_matches(event_key: str) -> dict | list:
    return _get(f"/event/{event_key}/matches")