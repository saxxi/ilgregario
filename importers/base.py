from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass
class RaceMeta:
    name: str
    pcs_slug: str
    race_type: Literal["one_day", "stage_race"]
    result_path: str
    race_date: date | None
    winner_slug: str


@dataclass
class RiderResult:
    position: int
    rider_slug: str


@dataclass
class RiderProfile:
    slug: str
    full_name: str
    nationality: str
    team: str


class BaseImporter(ABC):
    @abstractmethod
    def fetch_calendar(self, year: int, max_races: int, completed_only: bool = True) -> list[RaceMeta]: ...

    @abstractmethod
    def fetch_num_stages(self, race: RaceMeta) -> int | None: ...

    @abstractmethod
    def fetch_results(self, race: RaceMeta) -> list[RiderResult]: ...

    @abstractmethod
    def fetch_rider(self, slug: str) -> RiderProfile: ...
