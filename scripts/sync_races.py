"""
Sync latest completed WorldTour races into the database.

Run as CLI:  python scripts/sync_races.py
Also called from:  GET /sync-races  (see routers/admin.py)
"""

import sys
import os
import logging
from datetime import datetime, timezone

# Allow imports from project root when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from importers import BaseImporter, RaceMeta
from importers.pcs import PCSImporter
from scoring import gc_points

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

YEAR = 2026
MAX_RACES = 50


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _upsert_athlete(db, importer: BaseImporter, rider_slug: str) -> str | None:
    resp = db.table("athletes").select("id").eq("pcs_slug", rider_slug).execute()
    if resp.data:
        return resp.data[0]["id"]

    log.info("  Fetching rider profile: %s", rider_slug)
    profile = importer.fetch_rider(rider_slug)
    insert_resp = db.table("athletes").insert({
        "pcs_slug": rider_slug,
        "full_name": profile.full_name,
        "nationality": profile.nationality,
        "team": profile.team,
    }).execute()
    if insert_resp.data:
        return insert_resp.data[0]["id"]
    log.warning("  Failed to insert athlete %s", rider_slug)
    return None


def _resolve_season_id(db) -> str | None:
    resp = db.table("seasons").select("id").eq("year", YEAR).eq("active", True).limit(1).execute()
    if resp.data:
        return resp.data[0]["id"]
    # Fall back to any season for this year
    resp = db.table("seasons").select("id").eq("year", YEAR).limit(1).execute()
    return resp.data[0]["id"] if resp.data else None


def _upsert_race(db, race: RaceMeta, num_stages: int | None, season_id: str | None = None) -> str | None:
    row = {
        "pcs_slug": race.pcs_slug,
        "name": race.name,
        "year": YEAR,
        "race_type": race.race_type,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    if race.race_date:
        row["race_date"] = race.race_date.isoformat()
    if num_stages:
        row["num_stages"] = num_stages
    if season_id:
        row["season_id"] = season_id

    resp = db.table("races").upsert(row, on_conflict="pcs_slug").execute()
    if resp.data:
        return resp.data[0]["id"]
    log.warning("Upsert failed for race %s", race.pcs_slug)
    return None


def _upsert_result(db, race_id: str, athlete_id: str, position: int,
                   points: int, result_type: str, stage_number: int = 0) -> None:
    db.table("race_results").upsert(
        {
            "race_id": race_id,
            "athlete_id": athlete_id,
            "position": position,
            "points": points,
            "result_type": result_type,
            "stage_number": stage_number,
        },
        on_conflict="race_id,athlete_id,result_type,stage_number",
    ).execute()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def sync(db=None, importer: BaseImporter | None = None) -> dict:
    """
    Sync latest completed WT races.
    Returns a summary dict suitable for use in an API response.
    """
    if db is None:
        db = get_db()
    if importer is None:
        importer = PCSImporter()

    log.info("Fetching %d WT calendar…", YEAR)
    races = importer.fetch_calendar(year=YEAR, max_races=MAX_RACES, completed_only=False)
    completed_races = [r for r in races if r.winner_slug]
    upcoming_races  = [r for r in races if not r.winner_slug]
    log.info("Found %d completed, %d upcoming races", len(completed_races), len(upcoming_races))

    season_id = _resolve_season_id(db)
    if season_id:
        log.info("Resolved season_id: %s", season_id)
    else:
        log.warning("No season found for year %d — races will have no season_id", YEAR)

    synced, skipped = 0, 0

    for race in completed_races:
        log.info("Syncing %s (%s)", race.name, race.pcs_slug)

        num_stages = importer.fetch_num_stages(race) if race.race_type == "stage_race" else None

        race_id = _upsert_race(db, race, num_stages, season_id=season_id)
        if not race_id:
            skipped += 1
            continue

        results = importer.fetch_results(race)
        if not results:
            log.warning("  No results found for %s", race.pcs_slug)
            skipped += 1
            continue

        for result in results:
            athlete_id = _upsert_athlete(db, importer, result.rider_slug)
            if not athlete_id:
                continue
            pts = gc_points(race.name, num_stages, result.position)
            _upsert_result(
                db,
                race_id=race_id,
                athlete_id=athlete_id,
                position=result.position,
                points=pts,
                result_type="gc",
            )

        log.info("  Synced %d results", len(results))
        synced += 1

    for race in upcoming_races:
        log.info("Upserting upcoming race %s (%s)", race.name, race.pcs_slug)
        num_stages = None  # don't fetch stages for upcoming races
        race_id = _upsert_race(db, race, num_stages, season_id=season_id)
        if race_id:
            synced += 1
        else:
            skipped += 1

    summary = {
        "synced": synced,
        "skipped": skipped,
        "total": len(races),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    log.info("Done: %s", summary)
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["pcs", "json"], default="pcs")
    parser.add_argument("--path", default=None,
                        help="Path to data file (JSON or CSV). Defaults to tmp/pcs_reference.json or tmp/pcs_calendar.csv")
    parser.add_argument("--cache", default="tmp/pcs_html",
                        help="Directory to cache raw PCS HTML (only used with --source pcs)")
    parser.add_argument("--no-cache", dest="cache", action="store_false",
                        help="Disable HTML caching")
    args = parser.parse_args()

    if args.source == "json":
        from importers.json_file import JSONFileImporter
        path = args.path or "tmp/pcs_reference.json"
        _importer = JSONFileImporter(path)
    else:
        _importer = PCSImporter(cache_dir=args.cache or None)

    print(sync(importer=_importer))
