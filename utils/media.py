import os

_ATHLETE_PHOTO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "images", "athletes")


def athlete_photo_url(pcs_slug: str) -> str | None:
    if not pcs_slug:
        return None
    path = os.path.join(_ATHLETE_PHOTO_DIR, f"{pcs_slug}.png")
    return f"/static/images/athletes/{pcs_slug}.png" if os.path.isfile(path) else None
