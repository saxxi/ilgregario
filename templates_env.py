from fastapi.templating import Jinja2Templates
from auth import make_csrf_token

templates = Jinja2Templates(directory="templates")


def _fmt_credits(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}M"


templates.env.filters["fmt_credits"] = _fmt_credits
templates.env.globals["csrf_token"] = make_csrf_token
