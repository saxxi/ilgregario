"""Importer that reads from a local JSON reference file (no network)."""

import json
import re
import logging
from datetime import date

from .base import BaseImporter, RaceMeta, RiderProfile, RiderResult

log = logging.getLogger(__name__)

# Maps sample_results keys in the JSON to their pcs_slug
_RESULTS_KEY_TO_SLUG = {
    "liege_bastogne_liege_2026": "liege-bastogne-liege",
    "paris_nice_2026_gc": "paris-nice",
}


class JSONFileImporter(BaseImporter):
    def __init__(self, path: str) -> None:
        with open(path) as f:
            self._data = json.load(f)

        self._results: dict[str, list[dict]] = {
            slug: self._data["sample_results"][key]
            for key, slug in _RESULTS_KEY_TO_SLUG.items()
            if key in self._data.get("sample_results", {})
        }
        # team lookup built from result rows so unknown riders still get a team
        self._team_by_slug: dict[str, str] = {
            row["rider_slug"]: row["team"]
            for rows in self._results.values()
            for row in rows
            if row.get("rider_slug") and row.get("team")
        }

    # ------------------------------------------------------------------
    # BaseImporter implementation
    # ------------------------------------------------------------------

    def fetch_calendar(self, year: int, max_races: int, completed_only: bool = True) -> list[RaceMeta]:
        entries = self._data.get("calendar_2026_wt", [])
        all_races = [
            RaceMeta(
                name=entry["name"],
                pcs_slug=entry["pcs_slug"],
                race_type=entry["race_type"],
                result_path=entry["result_url"],
                race_date=_parse_date(entry.get("start_date", ""), year),
                winner_slug=entry.get("winner_slug", ""),
            )
            for entry in entries
        ]
        if completed_only:
            completed = [r for r in reversed(all_races) if r.winner_slug]
            return completed[:max_races]
        completed = [r for r in reversed(all_races) if r.winner_slug][:max_races]
        upcoming  = [r for r in all_races if not r.winner_slug]
        return completed + upcoming

    def fetch_num_stages(self, race: RaceMeta) -> int | None:
        for entry in self._data.get("calendar_2026_wt", []):
            if entry["pcs_slug"] == race.pcs_slug:
                return _stages_from_range(entry.get("date_range", ""))
        return None

    def fetch_results(self, race: RaceMeta) -> list[RiderResult]:
        if race.pcs_slug in self._results:
            results = []
            for row in self._results[race.pcs_slug]:
                try:
                    pos = int(row["pos"])
                except (ValueError, KeyError):
                    continue
                if pos > 10:
                    break
                results.append(RiderResult(position=pos, rider_slug=row["rider_slug"]))
            return results

        # Fall back to winner-only from calendar entry
        if race.winner_slug:
            log.info("  No full results for %s — using winner only", race.pcs_slug)
            return [RiderResult(position=1, rider_slug=race.winner_slug)]
        return []

    def fetch_rider(self, slug: str) -> RiderProfile:
        profiles = self._data.get("rider_profiles", {})
        if slug in profiles:
            p = profiles[slug]
            return RiderProfile(
                slug=slug,
                full_name=p.get("full_name", _slug_to_name(slug)),
                nationality=p.get("nationality", ""),
                team=p.get("team", self._team_by_slug.get(slug, "")),
            )
        return RiderProfile(
            slug=slug,
            full_name=_slug_to_name(slug),
            nationality="",
            team=self._team_by_slug.get(slug, ""),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_date(value: str, year: int) -> date | None:
    m = re.match(r"^(\d{1,2})\.(\d{1,2})$", value.strip())
    if not m:
        return None
    try:
        return date(year, int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _stages_from_range(date_range: str) -> int | None:
    """'08.03 - 15.03' → 7 (end day minus start day)."""
    m = re.match(r"(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})", date_range)
    if not m:
        return None
    try:
        start = date(2026, int(m.group(2)), int(m.group(1)))
        end = date(2026, int(m.group(4)), int(m.group(3)))
        return (end - start).days
    except ValueError:
        return None


def _slug_to_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))
