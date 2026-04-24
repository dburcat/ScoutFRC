from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional, Union
from datetime import date, datetime


class EventBase(BaseModel):
    tba_event_key: str
    name: str
    location: Optional[str] = None
    start_date: date
    end_date: date
    season_year: int
    perspective_matrix: Optional[Union[dict, list]] = None


class EventCreate(EventBase):
    pass


class Event_schema(EventBase):
    event_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def team_count(self) -> int:
        """Distinct teams that have a RobotPerformance in any match of this event."""
        try:
            team_ids = set()
            for match in self.matches:  # type: ignore[attr-defined]
                for perf in match.robot_performances:
                    team_ids.add(perf.team_id)
            return len(team_ids)
        except AttributeError:
            return 0

    @computed_field
    @property
    def match_count(self) -> int:
        try:
            return len(self.matches)  # type: ignore[attr-defined]
        except AttributeError:
            return 0