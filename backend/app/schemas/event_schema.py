from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional, Union, List, TYPE_CHECKING
from datetime import date, datetime

if TYPE_CHECKING:
    from .match_schema import Match_schema


class EventBase(BaseModel):
    tba_event_key: str
    name: str
    city: Optional[str] = None
    state_prov: Optional[str] = None
    country: Optional[str] = None
    start_date: date
    end_date: date
    season_year: int
    perspective_matrix: Optional[Union[dict, list]] = None


class EventCreate(EventBase):
    pass


class EventSummary_schema(EventBase):
    """Lightweight schema for list endpoints — no nested matches.
    team_count and match_count are injected by the router via SQL COUNT queries,
    not computed from nested ORM relationships."""
    event_id: int
    created_at: datetime
    team_count: int = 0
    match_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def location(self) -> Optional[str]:
        parts = [p for p in [self.city, self.state_prov, self.country] if p]
        return ", ".join(parts) if parts else None


class Event_schema(EventBase):
    """Full schema for single-event detail — includes nested matches."""
    event_id: int
    created_at: datetime
    matches: List["Match_schema"] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def location(self) -> Optional[str]:
        parts = [p for p in [self.city, self.state_prov, self.country] if p]
        return ", ".join(parts) if parts else None

    @computed_field
    @property
    def team_count(self) -> int:
        team_ids: set[int] = set()
        for match in self.matches:
            for alliance in match.alliances:
                for perf in alliance.robot_performances:
                    team_ids.add(perf.team_id)
        return len(team_ids)

    @computed_field
    @property
    def match_count(self) -> int:
        return len(self.matches)


# Resolve forward reference
from .match_schema import Match_schema  # noqa: E402
Event_schema.model_rebuild()