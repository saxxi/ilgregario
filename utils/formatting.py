from datetime import date

MONTHS_IT = ["", "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


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
