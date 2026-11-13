import requests

from . import const, errors
from .stats import _minutes

DAY_SHORT = {
    "monday": "Пн",
    "tuesday": "Вт",
    "wednesday": "Ср",
    "thursday": "Чт",
    "friday": "Пт",
    "saturday": "Сб",
    "sunday": "Вс",
}

DAY_STATUS_ICON = {
    "closed": "✅",
    "partial": "🟡",
    "open": "🔴",
    "today": "📍",
    "future": "·",
    "none": "▫️",
}


def GetDebt() -> dict:
    """GET /api/v1/debt → the DebtSummary (`total_minutes`, `items`, `today_remaining`, `days`)."""
    response = requests.get(const.DEBT_URI)
    if response.status_code != 200:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))
    try:
        return response.json().get("data") or {}
    except ValueError:
        raise errors.InvalidStatusCode("GET request returned an invalid JSON response")


def DebtByTask(debt: dict) -> dict[str, int]:
    """Total debt minutes per task, in the server's order (oldest day first)."""
    totals: dict[str, int] = {}
    for item in debt.get("items") or []:
        name = item.get("task_name", "")
        remaining = item.get("remaining", 0)
        if name and remaining > 0:
            totals[name] = totals.get(name, 0) + remaining
    return totals


def _week_strip(debt: dict) -> str:
    days = debt.get("days") or []
    return " ".join(
        f"{DAY_SHORT.get(d.get('day', ''), d.get('day', '')[:2])}{DAY_STATUS_ICON.get(d.get('status', ''), '')}"
        for d in days
    )


def FormatDebt(debt: dict) -> str:
    total = debt.get("total_minutes", 0)
    strip = _week_strip(debt)
    if not total:
        lines = ["💳 Долга нет 🎉"]
    else:
        lines = [f"💳 Долг прошлых дней: {_minutes(total)}", ""]
        per_day: dict[str, list[str]] = {}
        for item in debt.get("items") or []:
            name = item.get("task_name", "")
            if not name or item.get("remaining", 0) <= 0:
                continue
            day = DAY_SHORT.get(item.get("day", ""), item.get("day", ""))
            per_day.setdefault(name, []).append(f"{day} {item['remaining']}")
        for name, minutes in DebtByTask(debt).items():
            lines.append(f"• {name} — {_minutes(minutes)} ({', '.join(per_day.get(name, []))})")
    if strip:
        lines.append(f"\n{strip}")
    today_remaining = debt.get("today_remaining")
    if today_remaining:
        lines.append(f"Сегодня осталось: {_minutes(today_remaining)}")
    return "\n".join(lines)
