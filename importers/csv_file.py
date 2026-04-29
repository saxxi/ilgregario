"""Importer that reads from a local CSV calendar file (no network)."""

import csv
import logging
from datetime import date

from .base import BaseImporter, RaceMeta, RiderProfile, RiderResult

log = logging.getLogger(__name__)

_CSV_TYPE_MAP = {
    "stage race": "stage_race",
    "grand tour": "stage_race",
    "one-day classic": "one_day",
    "monument": "one_day",
    "one-day": "one_day",
    "one day": "one_day",
    "time trial": "one_day",
    "mixed/championship": "one_day",
}


class CSVFileImporter(BaseImporter):
    def __init__(self, path: str) -> None:
        self._races: list[dict] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("PCS Slug"):
                    self._races.append(row)

    def fetch_calendar(self, year: int, max_races: int, completed_only: bool = True) -> list[RaceMeta]:
        all_races = [self._to_meta(r) for r in self._races]
        completed = [r for r in all_races if r.winner_slug]
        upcoming = [r for r in all_races if not r.winner_slug]
        if completed_only:
            return completed[:max_races]
        return completed[:max_races] + upcoming

    def fetch_num_stages(self, race: RaceMeta) -> int | None:
        for row in self._races:
            if row["PCS Slug"] == race.pcs_slug:
                return _stages_from_date_range(row["Date"])
        return None

    def fetch_results(self, race: RaceMeta) -> list[RiderResult]:
        if race.winner_slug:
            log.info("  Winner-only result for %s", race.pcs_slug)
            return [RiderResult(position=1, rider_slug=race.winner_slug)]
        return []

    def fetch_rider(self, slug: str) -> RiderProfile:
        return RiderProfile(
            slug=slug,
            full_name=_slug_to_name(slug),
            nationality="",
            team="",
        )

    def _to_meta(self, row: dict) -> RaceMeta:
        date_str = row["Date"]
        race_date = _parse_start_date(date_str)
        raw_type = row.get("Type", "").lower().strip()
        race_type = _CSV_TYPE_MAP.get(raw_type, "one_day")
        slug = row["PCS Slug"].strip()
        result_path = f"race/{slug}/2026/{'gc' if race_type == 'stage_race' else 'result'}"
        return RaceMeta(
            name=row["Race Name"].strip(),
            pcs_slug=slug,
            race_type=race_type,
            result_path=result_path,
            race_date=race_date,
            winner_slug=row.get("Winner Slug", "").strip(),
        )


def _parse_start_date(value: str) -> date | None:
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DD to YYYY-MM-DD' → start date."""
    part = value.split(" to ")[0].strip()
    try:
        return date.fromisoformat(part)
    except ValueError:
        return None


def _stages_from_date_range(value: str) -> int | None:
    """'YYYY-MM-DD to YYYY-MM-DD' → number of days between start and end."""
    parts = value.split(" to ")
    if len(parts) != 2:
        return None
    try:
        start = date.fromisoformat(parts[0].strip())
        end = date.fromisoformat(parts[1].strip())
        return (end - start).days
    except ValueError:
        return None


def _slug_to_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))
