"""
Fetch athlete photos from Wikipedia and save processed versions.

  Raw originals  → static/images/athletes/raw/{slug}.jpg  (kept as-is)
  Processed      → static/images/athletes/{pcs_slug}.png  (300×400, head-biased crop)
  No-image log   → static/images/athletes/no-image.txt    (one pcs_slug per line)

Usage:
    python scripts/fetch_athlete_photos.py            # new athletes only (skips no-image list)
    python scripts/fetch_athlete_photos.py --retry    # retry athletes in no-image.txt
    python scripts/fetch_athlete_photos.py --refetch  # overwrite all existing photos
    python scripts/fetch_athlete_photos.py --slug tadej-pogacar
"""

import argparse
import logging
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_HEADERS = {"User-Agent": "IlGregario/1.0 (https://github.com/saxxi; a.saxena.email@gmail.com)"}
_WIKI_API = "https://en.wikipedia.org/w/api.php"

_BASE = Path(__file__).parent.parent / "static" / "images" / "athletes"
_RAW_DIR = _BASE / "raw"
_OUT_DIR = _BASE
_NO_IMAGE_FILE = _BASE / "no-image.txt"

_OUT_W = 300
_OUT_H = 400

_RETRY_DELAYS = [2, 5, 15]


def _load_no_image_set() -> set[str]:
    if not _NO_IMAGE_FILE.exists():
        return set()
    return {line.strip() for line in _NO_IMAGE_FILE.read_text().splitlines() if line.strip()}


def _add_to_no_image(pcs_slug: str) -> None:
    existing = _load_no_image_set()
    if pcs_slug not in existing:
        with _NO_IMAGE_FILE.open("a") as f:
            f.write(pcs_slug + "\n")


def _remove_from_no_image(pcs_slug: str) -> None:
    existing = _load_no_image_set()
    existing.discard(pcs_slug)
    _NO_IMAGE_FILE.write_text("\n".join(sorted(existing)) + "\n")


def _get(params: dict, label: str) -> dict | None:
    for attempt, wait in enumerate([0] + _RETRY_DELAYS):
        if wait:
            log.debug("Rate limited, retrying in %ds...", wait)
            time.sleep(wait)
        try:
            r = requests.get(_WIKI_API, params=params, headers=_HEADERS, timeout=10)
            if r.status_code == 429:
                continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if attempt == len(_RETRY_DELAYS):
                log.warning("Failed after retries: %s", label)
            continue
        except Exception as e:
            log.warning("Wikipedia API error for %r: %s", label, e)
            return None
    log.warning("Gave up after rate-limit retries: %s", label)
    return None


def _wiki_image_url(name: str) -> str | None:
    words = name.split()
    reversed_name = " ".join(words[1:] + words[:1]) if len(words) >= 2 else name

    data = _get({
        "action": "query",
        "titles": f"{reversed_name}|{name}",
        "prop": "pageimages",
        "format": "json",
        "pithumbsize": 800,
        "redirects": 1,
    }, name)

    if data:
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if int(page_id) > 0:
                src = page.get("thumbnail", {}).get("source")
                if src:
                    return src

    search_data = _get({
        "action": "query",
        "list": "search",
        "srsearch": f"{reversed_name} cyclist",
        "srlimit": 1,
        "format": "json",
    }, f"{name} search")

    if search_data:
        results = search_data.get("query", {}).get("search", [])
        if results:
            title = results[0]["title"]
            page_data = _get({
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 800,
            }, title)
            if page_data:
                pages = page_data.get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    if int(page_id) > 0:
                        src = page.get("thumbnail", {}).get("source")
                        if src:
                            return src

    return None


def _crop_portrait(img: Image.Image) -> Image.Image:
    w, h = img.size
    target_ratio = _OUT_W / _OUT_H

    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        img = img.crop((0, 0, w, new_h))

    return img.resize((_OUT_W, _OUT_H), Image.LANCZOS)


def fetch_one(name: str, slug: str, pcs_slug: str, refetch: bool = False) -> bool:
    out_name = pcs_slug or slug
    raw_path = _RAW_DIR / f"{slug}.jpg"
    out_path = _OUT_DIR / f"{out_name}.png"

    if out_path.exists() and not refetch:
        return True

    url = _wiki_image_url(name)
    if not url:
        log.warning("NO IMAGE  %s", name)
        _add_to_no_image(out_name)
        return False

    raw_bytes = None
    for attempt, wait in enumerate([0] + _RETRY_DELAYS):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, headers=_HEADERS, timeout=15)
            if r.status_code == 429:
                continue
            r.raise_for_status()
            raw_bytes = r.content
            break
        except requests.HTTPError:
            continue
        except Exception as e:
            log.warning("DOWNLOAD FAILED  %s: %s", name, e)
            return False
    if raw_bytes is None:
        log.warning("DOWNLOAD FAILED after retries  %s", name)
        _add_to_no_image(out_name)
        return False

    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_bytes)

    try:
        img = Image.open(BytesIO(raw_bytes)).convert("RGB")
        processed = _crop_portrait(img)
        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        processed.save(out_path, "PNG")
    except Exception as e:
        log.warning("PROCESS FAILED  %s: %s", name, e)
        _add_to_no_image(out_name)
        return False

    log.info("OK  %s → %s", name, out_path.name)
    _remove_from_no_image(out_name)
    return True


def run_missing() -> dict:
    """Fetch photos for athletes not yet tried. Callable from other modules."""
    db = get_db()
    athletes = db.table("athletes").select("full_name,pcs_slug,slug").order("full_name").execute().data
    no_image = _load_no_image_set()
    ok = fail = skip = 0
    for ath in athletes:
        name = ath["full_name"]
        slug = ath["slug"]
        pcs_slug = ath.get("pcs_slug") or ""
        out_name = pcs_slug or slug
        if (_OUT_DIR / f"{out_name}.png").exists() or out_name in no_image:
            skip += 1
            continue
        if fetch_one(name, slug, pcs_slug):
            ok += 1
        else:
            fail += 1
        time.sleep(1)
    log.info("fetch-photos done — ok: %d  failed: %d  skipped: %d", ok, fail, skip)
    return {"ok": ok, "fail": fail, "skip": skip}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true",
                        help="Retry athletes listed in no-image.txt")
    parser.add_argument("--refetch", action="store_true",
                        help="Overwrite existing photos (all athletes)")
    parser.add_argument("--slug", help="Process a single athlete by pcs_slug")
    args = parser.parse_args()

    db = get_db()

    if args.slug:
        rows = db.table("athletes").select("full_name,pcs_slug,slug").eq("pcs_slug", args.slug).execute().data
        if not rows:
            rows = db.table("athletes").select("full_name,pcs_slug,slug").eq("slug", args.slug).execute().data
        if not rows:
            log.error("Athlete not found: %s", args.slug)
            return
        ath = rows[0]
        fetch_one(ath["full_name"], ath["slug"], ath.get("pcs_slug") or "", refetch=True)
        return

    if args.retry:
        no_image = _load_no_image_set()
        if not no_image:
            log.info("no-image.txt is empty — nothing to retry")
            return
        log.info("Retrying %d athletes from no-image.txt", len(no_image))
        rows = db.table("athletes").select("full_name,pcs_slug,slug").execute().data
        slug_map = {(r.get("pcs_slug") or r["slug"]): r for r in rows}
        ok = fail = skip = 0
        for out_name in sorted(no_image):
            ath = slug_map.get(out_name)
            if not ath:
                log.warning("UNKNOWN SLUG in no-image.txt: %s", out_name)
                skip += 1
                continue
            if fetch_one(ath["full_name"], ath["slug"], ath.get("pcs_slug") or "", refetch=True):
                ok += 1
            else:
                fail += 1
            time.sleep(1)
        log.info("Retry done — ok: %d  failed: %d  skipped: %d", ok, fail, skip)
        return

    # Default: new athletes only (skip those with photos AND those in no-image.txt)
    no_image = _load_no_image_set()
    athletes = db.table("athletes").select("full_name,pcs_slug,slug").order("full_name").execute().data
    log.info("%d athletes in DB, %d in no-image list", len(athletes), len(no_image))
    ok = fail = skip = 0
    for ath in athletes:
        name = ath["full_name"]
        slug = ath["slug"]
        pcs_slug = ath.get("pcs_slug") or ""
        out_name = pcs_slug or slug
        if (_OUT_DIR / f"{out_name}.png").exists() and not args.refetch:
            skip += 1
            continue
        if out_name in no_image and not args.refetch:
            skip += 1
            continue
        if fetch_one(name, slug, pcs_slug, refetch=args.refetch):
            ok += 1
        else:
            fail += 1
        time.sleep(1)
    log.info("Done — ok: %d  failed: %d  skipped: %d", ok, fail, skip)


if __name__ == "__main__":
    main()
