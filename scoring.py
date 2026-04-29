from config import GC_SCORING, STAGE_SCORING


def gc_points(race_name: str, num_stages: int | None, position: int) -> int:
    idx = position - 1
    for key, table in GC_SCORING["by_name"].items():
        if key.lower() in race_name.lower():
            return table[idx] if idx < len(table) else 0
    if num_stages is not None:
        for threshold, table in GC_SCORING["by_stages"]:
            if num_stages <= threshold:
                return table[idx] if idx < len(table) else 0
    default = GC_SCORING["default"]
    return default[idx] if idx < len(default) else 0


def stage_points(race_name: str, num_stages: int | None, position: int) -> int:
    idx = position - 1
    for key, table in STAGE_SCORING["by_name"].items():
        if key.lower() in race_name.lower():
            return table[idx] if idx < len(table) else 0
    if num_stages is not None:
        for threshold, table in STAGE_SCORING["by_stages"]:
            if num_stages <= threshold:
                return table[idx] if idx < len(table) else 0
    default = STAGE_SCORING["default"]
    return default[idx] if idx < len(default) else 0


_STATUS_POINTS = {
    'ok':  lambda rt, name, stages, pos: (
        gc_points(name, stages, pos) if rt == 'gc' else stage_points(name, stages, pos)
    ) if pos else 0,
    'dnf': lambda rt, name, stages, pos: 0,
    'dns': lambda rt, name, stages, pos: 0,
}


def score_result(result_type: str, race_name: str, num_stages: int | None,
                 position: int | None, status: str = 'ok') -> int:
    handler = _STATUS_POINTS.get(status, _STATUS_POINTS['ok'])
    return handler(result_type, race_name, num_stages, position)
