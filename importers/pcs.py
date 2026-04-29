"""ProcyclingStats importer from procyclingstats.com."""

import os
import re
import time
import logging
from datetime import date

import requests
from bs4 import BeautifulSoup

from .base import BaseImporter, RaceMeta, RiderProfile, RiderResult

log = logging.getLogger(__name__)

_BASE_URL = "https://www.procyclingstats.com"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IlGregario/1.0)"}


class PCSImporter(BaseImporter):
    def __init__(self, base_url: str = _BASE_URL, polite_delay: float = 0.5,
                 cache_dir: str | None = None) -> None:
        self._base_url = base_url
        self._delay = polite_delay
        self._cache_dir = cache_dir

    # ------------------------------------------------------------------
    # BaseImporter implementation
    # ------------------------------------------------------------------

    def fetch_calendar(self, year: int, max_races: int, completed_only: bool = True) -> list[RaceMeta]:
        soup = self._get(f"races.php?year={year}&circuit=1&filter=Filter")
        table = soup.find("table")
        if not table:
            log.warning("No calendar table found")
            return []

        completed: list[RaceMeta] = []
        upcoming: list[RaceMeta] = []

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            links = row.find_all("a")
            if len(cols) < 4:
                continue

            has_winner = bool(cols[3].get_text(strip=True))
            if not has_winner and completed_only:
                continue

            race_link = links[0].get("href", "") if links else ""
            winner_link = links[1].get("href", "") if (has_winner and len(links) > 1) else ""

            if "/gc" in race_link:
                race_type = "stage_race"
            elif "/result" in race_link:
                race_type = "one_day"
            elif not has_winner:
                # Upcoming race: infer type from date column (range = stage race)
                date_text = cols[0].get_text(strip=True)
                race_type = "stage_race" if " - " in date_text else "one_day"
                suffix = "/gc" if race_type == "stage_race" else "/result"
                race_link = race_link.rstrip("/") + suffix
            else:
                continue

            pcs_slug = race_link.split("/")[1] if "/" in race_link else ""
            if not pcs_slug:
                continue

            meta = RaceMeta(
                name=cols[2].get_text(strip=True),
                pcs_slug=pcs_slug,
                race_type=race_type,
                result_path=race_link,
                race_date=self._parse_date(cols[1].get_text(strip=True), year),
                winner_slug=winner_link.replace("rider/", "") if winner_link else "",
            )
            if has_winner:
                completed.append(meta)
            else:
                upcoming.append(meta)

        completed.reverse()  # most-recent first
        if completed_only:
            return completed[:max_races]
        return completed[:max_races] + upcoming

    def fetch_num_stages(self, race: RaceMeta) -> int | None:
        soup = self._get(race.result_path)
        nums = [
            int(m.group(1))
            for a in soup.find_all("a", href=True)
            if (m := re.search(r"/stage-(\d+)", a["href"]))
        ]
        return max(nums) if nums else None

    def fetch_results(self, race: RaceMeta) -> list[RiderResult]:
        soup = self._get(race.result_path)
        table = soup.find("table")
        if not table:
            return []

        min_cols = 7 if race.race_type == "one_day" else 9
        results: list[RiderResult] = []

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < min_cols:
                continue

            links = [a.get("href", "") for a in row.find_all("a")]
            rider_link = next((l for l in links if l.startswith("rider/")), "")
            if not rider_link:
                continue

            rider_slug = rider_link.replace("rider/", "").split("/")[0]
            try:
                pos = int(cells[0].get_text(strip=True))
            except ValueError:
                continue

            if pos > 10:
                break

            results.append(RiderResult(position=pos, rider_slug=rider_slug))

        return results

    def fetch_rider(self, slug: str) -> RiderProfile:
        soup = self._get(f"rider/{slug}")

        title_div = soup.find("div", class_="title")
        full_name = title_div.get_text(strip=True) if title_div else slug

        nationality = ""
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if text.startswith("Nationality:"):
                a = li.find("a")
                nationality = a.get_text(strip=True) if a else text.replace("Nationality:", "").strip()
                break

        subtitle = soup.find("div", class_="subtitle")
        team = subtitle.get_text(strip=True) if subtitle else ""

        return RiderProfile(slug=slug, full_name=full_name, nationality=nationality, team=team)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> BeautifulSoup:
        if self._cache_dir:
            cache_file = os.path.join(
                self._cache_dir,
                re.sub(r"[^a-zA-Z0-9._-]", "_", path) + ".html",
            )
            if os.path.exists(cache_file):
                log.info("CACHE %s", cache_file)
                with open(cache_file, encoding="utf-8") as f:
                    return BeautifulSoup(f.read(), "html.parser")

        url = f"{self._base_url}/{path}"
        log.info("GET %s", url)
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        time.sleep(self._delay)

        if self._cache_dir:
            os.makedirs(self._cache_dir, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(r.text)
            log.info("SAVED %s", cache_file)

        return BeautifulSoup(r.text, "html.parser")

    @staticmethod
    def _parse_date(value: str, year: int) -> date | None:
        """Convert PCS date string '01.02' to date(year, 2, 1)."""
        m = re.match(r"^(\d{1,2})\.(\d{1,2})$", value.strip())
        if not m:
            return None
        try:
            return date(year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
