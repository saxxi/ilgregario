"""
Bulk-import all riders from PCS team rosters into the athletes table.

Usage:
    python scripts/import_athletes.py                     # WorldTeams only
    python scripts/import_athletes.py --circuit ProTeams  # add ProTeams
    python scripts/import_athletes.py --no-cache          # skip HTML cache
"""

import sys
import os
import re
import time
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
from database import get_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

_BASE_URL = "https://www.procyclingstats.com"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IlGregario/1.0)"}
_DELAY = 0.5

_FLAG_TO_COUNTRY = {
    "af": "Afghanistan", "al": "Albania", "dz": "Algeria", "ad": "Andorra",
    "ao": "Angola", "ar": "Argentina", "am": "Armenia", "au": "Australia",
    "at": "Austria", "az": "Azerbaijan", "bh": "Bahrain", "by": "Belarus",
    "be": "Belgium", "bj": "Benin", "bo": "Bolivia", "ba": "Bosnia",
    "bw": "Botswana", "br": "Brazil", "bg": "Bulgaria", "bf": "Burkina Faso",
    "cm": "Cameroon", "ca": "Canada", "cv": "Cape Verde", "cl": "Chile",
    "cn": "China", "co": "Colombia", "cr": "Costa Rica", "hr": "Croatia",
    "cu": "Cuba", "cz": "Czech Republic", "dk": "Denmark", "do": "Dominican Republic",
    "ec": "Ecuador", "eg": "Egypt", "sv": "El Salvador", "er": "Eritrea",
    "ee": "Estonia", "et": "Ethiopia", "fi": "Finland", "fr": "France",
    "ga": "Gabon", "ge": "Georgia", "de": "Germany", "gh": "Ghana",
    "gr": "Greece", "gt": "Guatemala", "gn": "Guinea", "hn": "Honduras",
    "hk": "Hong Kong", "hu": "Hungary", "is": "Iceland", "in": "India",
    "id": "Indonesia", "ir": "Iran", "iq": "Iraq", "ie": "Ireland",
    "il": "Israel", "it": "Italy", "jm": "Jamaica", "jp": "Japan",
    "jo": "Jordan", "kz": "Kazakhstan", "ke": "Kenya", "xk": "Kosovo",
    "kw": "Kuwait", "kg": "Kyrgyzstan", "lv": "Latvia", "lb": "Lebanon",
    "ly": "Libya", "li": "Liechtenstein", "lt": "Lithuania", "lu": "Luxembourg",
    "mk": "North Macedonia", "mg": "Madagascar", "mw": "Malawi", "my": "Malaysia",
    "mv": "Maldives", "ml": "Mali", "mt": "Malta", "mr": "Mauritania",
    "mx": "Mexico", "md": "Moldova", "mc": "Monaco", "mn": "Mongolia",
    "me": "Montenegro", "ma": "Morocco", "mz": "Mozambique", "na": "Namibia",
    "nl": "Netherlands", "nz": "New Zealand", "ni": "Nicaragua", "ng": "Nigeria",
    "no": "Norway", "om": "Oman", "pk": "Pakistan", "pa": "Panama",
    "py": "Paraguay", "pe": "Peru", "ph": "Philippines", "pl": "Poland",
    "pt": "Portugal", "qa": "Qatar", "ro": "Romania", "ru": "Russia",
    "rw": "Rwanda", "sa": "Saudi Arabia", "sn": "Senegal", "rs": "Serbia",
    "si": "Slovenia", "so": "Somalia", "za": "South Africa", "es": "Spain",
    "lk": "Sri Lanka", "sd": "Sudan", "se": "Sweden", "ch": "Switzerland",
    "sy": "Syria", "tw": "Taiwan", "tj": "Tajikistan", "tz": "Tanzania",
    "th": "Thailand", "tg": "Togo", "tn": "Tunisia", "tr": "Turkey",
    "tm": "Turkmenistan", "ug": "Uganda", "ua": "Ukraine", "ae": "UAE",
    "gb": "Great Britain", "us": "USA", "uy": "Uruguay", "uz": "Uzbekistan",
    "ve": "Venezuela", "vn": "Vietnam", "ye": "Yemen", "zm": "Zambia",
    "zw": "Zimbabwe",
}


def _get(path: str, cache_dir: str | None) -> BeautifulSoup:
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        fname = re.sub(r"[^a-zA-Z0-9._-]", "_", path) + ".html"
        cache_file = os.path.join(cache_dir, fname)
        if os.path.exists(cache_file):
            log.debug("CACHE %s", cache_file)
            with open(cache_file, encoding="utf-8") as f:
                return BeautifulSoup(f.read(), "html.parser")

    url = f"{_BASE_URL}/{path}"
    log.info("GET %s", url)
    r = requests.get(url, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    time.sleep(_DELAY)

    if cache_dir:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(r.text)

    return BeautifulSoup(r.text, "html.parser")


def fetch_teams(year: int, circuits: list[str], cache_dir: str | None) -> list[tuple[str, str]]:
    """Return list of (team_name, team_slug) for requested circuits."""
    soup = _get(f"teams.php?year={year}&filter=Filter", cache_dir)
    lists = soup.find_all("ul", class_=lambda c: c and "lh18" in c)

    teams: list[tuple[str, str]] = []
    for ul in lists:
        heading_tag = ul.find_previous_sibling()
        while heading_tag and heading_tag.name not in ("h2", "h3", "h4"):
            heading_tag = heading_tag.find_previous_sibling()
        heading = heading_tag.get_text(strip=True) if heading_tag else ""

        if not any(c.lower() in heading.lower() for c in circuits):
            continue

        for li in ul.find_all("li"):
            a = li.find("a", href=True)
            if a and a["href"].startswith("team/"):
                slug = a["href"].replace("team/", "")
                teams.append((a.get_text(strip=True), slug))

    return teams


def fetch_roster(team_slug: str, team_name: str, cache_dir: str | None) -> list[dict]:
    """Return list of rider dicts for a team."""
    soup = _get(f"team/{team_slug}", cache_dir)

    rider_table = None
    for table in soup.find_all("table"):
        if table.find("a", href=lambda h: h and h.startswith("rider/")):
            rider_table = table
            break

    if not rider_table:
        log.warning("No rider table found for %s", team_slug)
        return []

    riders = []
    seen_slugs: set[str] = set()
    for row in rider_table.find_all("tr"):
        a = row.find("a", href=lambda h: h and h.startswith("rider/"))
        if not a:
            continue
        slug = a["href"].replace("rider/", "").strip("/")
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Title-case the name (stored as "SURNAME Firstname" on PCS)
        raw_name = a.get_text(strip=True)
        full_name = " ".join(w.capitalize() for w in raw_name.split())

        flag_span = row.find("span", class_=lambda c: c and "flag" in c)
        nat_code = ""
        nationality = ""
        if flag_span:
            classes = flag_span.get("class", [])
            nat_code = next((c for c in classes if c != "flag"), "")
            nationality = _FLAG_TO_COUNTRY.get(nat_code, nat_code.upper())

        riders.append({
            "pcs_slug": slug,
            "full_name": full_name,
            "nationality": nationality,
            "team": team_name,
        })

    return riders


def run(year: int = 2026, circuits: list[str] | None = None, cache_dir: str | None = "tmp/pcs_html") -> dict:
    if circuits is None:
        circuits = ["WorldTeam"]

    db = get_db()
    teams = fetch_teams(year, circuits, cache_dir)
    log.info("Found %d teams across circuits: %s", len(teams), circuits)

    inserted = updated = skipped = 0

    for team_name, team_slug in teams:
        log.info("Fetching roster: %s", team_name)
        riders = fetch_roster(team_slug, team_name, cache_dir)
        log.info("  %d riders", len(riders))

        for rider in riders:
            existing = db.table("athletes").select("id").eq("pcs_slug", rider["pcs_slug"]).execute()
            if existing.data:
                db.table("athletes").update({
                    "full_name": rider["full_name"],
                    "nationality": rider["nationality"],
                    "team": rider["team"],
                }).eq("pcs_slug", rider["pcs_slug"]).execute()
                updated += 1
            else:
                db.table("athletes").insert(rider).execute()
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
