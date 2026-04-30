"""
Bulk-import all riders from PCS team rosters into the athletes table.

Usage:
    python scripts/import_athletes.py                     # WorldTeams only
    python scripts/import_athletes.py --circuit ProTeams  # add ProTeams
    python scripts/import_athletes.py --no-cache          # skip HTML cache
"""

import sys
import os
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from utils import slugify
from importers.pcs import PCSImporter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run(year: int = 2026, circuits: list[str] | None = None, cache_dir: str | None = "tmp/pcs_html") -> dict:
    if circuits is None:
        circuits = ["WorldTeam"]

    db       = get_db()
    importer = PCSImporter(cache_dir=cache_dir)
    teams    = importer.fetch_teams(year, circuits)
    log.info("Found %d teams across circuits: %s", len(teams), circuits)

    inserted = updated = skipped = 0

    for team_name, team_slug in teams:
        log.info("Fetching roster: %s", team_name)
        riders = importer.fetch_roster(team_slug, team_name)
        log.info("  %d riders", len(riders))

        for rider in riders:
            slug     = rider["pcs_slug"] or slugify(rider["full_name"])
            existing = db.table("athletes").select("id").eq("pcs_slug", rider["pcs_slug"]).execute()
            if existing.data:
                db.table("athletes").update({
                    "full_name": rider["full_name"],
                    "nationality": rider["nationality"],
                    "team": rider["team"],
                    "slug": slug,
                }).eq("pcs_slug", rider["pcs_slug"]).execute()
                updated += 1
            else:
                db.table("athletes").insert({**rider, "slug": slug}).execute()
                inserted += 1

    summary = {"inserted": inserted, "updated": updated, "skipped": skipped, "teams": len(teams)}
    log.info("Done: %s", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuit", dest="circuits", action="append",
                        default=None,
                        help="Circuit name to include (default: WorldTeam). Can be repeated.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--cache", default="tmp/pcs_html")
    parser.add_argument("--no-cache", dest="cache", action="store_false")
    args = parser.parse_args()

    circuits = args.circuits or ["WorldTeam"]
    print(run(year=args.year, circuits=circuits, cache_dir=args.cache or None))
