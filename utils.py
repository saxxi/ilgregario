import os
import re
import unicodedata
from datetime import date

MONTHS_IT = ["", "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

AVATAR_COLORS = ["primary", "secondary", "accent", "success", "error", "warning"]

NATIONALITY_TO_FLAG_EMOJI: dict[str, str] = {
    "Slovenia": "🇸🇮", "Denmark": "🇩🇰", "Belgium": "🇧🇪", "Netherlands": "🇳🇱",
    "France": "🇫🇷", "Spain": "🇪🇸", "Colombia": "🇨🇴", "Italy": "🇮🇹",
    "Australia": "🇦🇺", "Great Britain": "🇬🇧", "United Kingdom": "🇬🇧",
    "Norway": "🇳🇴", "Germany": "🇩🇪", "Portugal": "🇵🇹", "Eritrea": "🇪🇷",
    "Ecuador": "🇪🇨", "United States": "🇺🇸", "Switzerland": "🇨🇭",
    "Ireland": "🇮🇪", "Poland": "🇵🇱", "Kazakhstan": "🇰🇿",
}

FLAG_CODE_TO_COUNTRY: dict[str, str] = {
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

_ATHLETE_PHOTO_DIR = os.path.join(os.path.dirname(__file__), "static", "images", "athletes")


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower())
    return slug.strip("-")


def flag_emoji(nationality: str | None) -> str:
    return NATIONALITY_TO_FLAG_EMOJI.get(nationality or "", "")


def athlete_photo_url(pcs_slug: str) -> str | None:
    if not pcs_slug:
        return None
    path = os.path.join(_ATHLETE_PHOTO_DIR, f"{pcs_slug}.png")
    return f"/static/images/athletes/{pcs_slug}.png" if os.path.isfile(path) else None


def fmt_date(race: dict) -> str:
    if not race.get("race_date"):
        return ""
    d = date.fromisoformat(race["race_date"])
    return f"{d.day} {MONTHS_IT[d.month]}"


def race_short(race: dict) -> str:
    name = race["name"]
    return "".join(w[0] for w in name.split()[:3]).upper()[:3]


def get_race_labels(races: list[dict]) -> list[str]:
    """Return short labels for chart axes, disambiguating any duplicate abbreviations."""
    shorts = [race_short(r) for r in races]
    totals: dict[str, int] = {}
    for s in shorts:
        totals[s] = totals.get(s, 0) + 1
    counts: dict[str, int] = {}
    result = []
    for s in shorts:
        if totals[s] > 1:
            counts[s] = counts.get(s, 0) + 1
            result.append(f"{s}{counts[s]}")
        else:
            result.append(s)
    return result
