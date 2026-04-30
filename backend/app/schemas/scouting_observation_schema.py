from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, Any
from datetime import datetime
import re


def _parse_set_number(tba_match_key: str | None) -> int | None:
    """Extract set number from TBA match key, e.g. '2025necmp_sf1m2' -> 1"""
    if not tba_match_key:
        return None
    m = re.search(r"(?:sf|f)(\d+)m\d+", tba_match_key)
    return int(m.group(1)) if m else None


class ScoutingObservationBase(BaseModel):
    team_id: int
    match_id: int
    scout_id: int
    notes: Optional[str] = None
    rating: Optional[int] = None  # 1-5
    actions: Optional[dict] = None


class ScoutingObservationCreate(ScoutingObservationBase):
    pass


# Used for writes — no extra fields, safe to pass to ScoutingObservation(**...)
class ScoutingObservation_schema(ScoutingObservationBase):
    observation_id: Optional[int] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Used for reads — includes denormalized display fields from joined relationships
class ScoutingObservationRead(ScoutingObservation_schema):
    match_number: Optional[int] = None
    match_set: Optional[int] = None   # set number for semis/finals (e.g. sf1m2 -> set 1)
    match_type: Optional[str] = None
    team_number: Optional[int] = None
    event_name: Optional[str] = None
    event_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_relationship_fields(cls, data: Any) -> Any:
        if hasattr(data, "__class__") and hasattr(data, "match"):
            match = getattr(data, "match", None)
            team = getattr(data, "team", None)
            tba_key = match.tba_match_key if match else None
            return {
                "observation_id": data.observation_id,
                "team_id": data.team_id,
                "match_id": data.match_id,
                "scout_id": data.scout_id,
                "notes": data.notes,
                "rating": data.rating,
                "actions": data.actions,
                "submitted_at": data.submitted_at,
                "match_number": match.match_number if match else None,
                "match_set": _parse_set_number(tba_key),
                "match_type": match.match_type if match else None,
                "team_number": team.team_number if team else None,
                "event_name": match.event.name if match and match.event else None,
                "event_key": match.event.tba_event_key if match and match.event else None,
            }
        return data