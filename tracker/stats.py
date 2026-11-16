import requests
from . import const, errors, timer

# Target of a bot start when the task has nothing left for today. A start without a target is a
# free timer, which the server stops after 20 minutes (watchdog safety cap).
DEFAULT_START_MINUTES = 30
PROGRESS_BAR_CELLS = 10

def GetTaskList() -> list[dict]:
    """Today's tasks: `today_tasks` of GET /dashboard/state, items with `name`, `role`,
    `time_duration`, `time_done`, `priority`. Raises errors.InvalidStatusCode on a non-200 answer."""
    return GetDashboardState().get("today_tasks") or []


def TaskRemaining(task: dict) -> int:
    """Minutes left today for a `today_tasks` item of GET /dashboard/state (never negative)."""
    return max(0, (task.get("time_duration") or 0) - (task.get("time_done") or 0))


def StartTarget(task_name: str) -> int:
    """Target for a bot start: what is left of the task today, else DEFAULT_START_MINUTES.
    Falls back to the default when the task list can't be read."""
    try:
        tasks = GetTaskList()
    except Exception:
        return DEFAULT_START_MINUTES
    for task in tasks or []:
        if (task.get("name") or task.get("task_name")) == task_name:
            remaining = TaskRemaining(task)
            return remaining if remaining > 0 else DEFAULT_START_MINUTES
    return DEFAULT_START_MINUTES


def GetDashboardState() -> dict:
    response = requests.get(const.DASHBOARD_STATE_URI)
    if response.status_code != 200:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))
    return response.json()


def _bar(done: int, total: int) -> str:
    filled = min(PROGRESS_BAR_CELLS, done * PROGRESS_BAR_CELLS // total) if total > 0 else 0
    return "▓" * filled + "░" * (PROGRESS_BAR_CELLS - filled)


def FormatToday(state: dict, debt_total: int | None = None) -> str:
    """Formats GET /api/v1/dashboard/state as the bot's "Сегодня" card."""
    total_planned = state.get("total_planned", 0)
    total_done = state.get("total_done", 0)
    pct = state.get("completion_pct", 0)
    lines = [
        f"📊 Сегодня: {_minutes(total_done)} из {_minutes(total_planned)} ({pct}%)",
        _bar(total_done, total_planned),
    ]

    running = state.get("running_task")
    if running and running.get("task_name"):
        elapsed_min = timer.ElapsedSeconds(running) // 60
        target = running.get("target_duration") or 0
        icon = "▶️ Идёт" if running.get("is_running") else "⏸ На паузе"
        progress = f"{elapsed_min} из {target}м" if target else f"{elapsed_min}м"
        lines.append(f"\n{icon}: {running['task_name']} — {progress}")

    tasks = state.get("today_tasks") or []
    open_tasks = [t for t in tasks if TaskRemaining(t) > 0]
    done_tasks = [t for t in tasks if TaskRemaining(t) == 0]
    if tasks:
        lines.append("")
    for t in open_tasks:
        lines.append(f"• {t['name']}: {t['time_done']}/{t['time_duration']}м — осталось {TaskRemaining(t)}м")
    for t in done_tasks:
        lines.append(f"✅ {t['name']}: {t['time_done']}/{t['time_duration']}м")
    if not tasks:
        lines.append("\nНа сегодня в расписании ничего нет.")

    if debt_total:
        lines.append(f"\n💳 Долг прошлых дней: {_minutes(debt_total)}")
    return "\n".join(lines)


def GetNextTask() -> str:
    response = requests.get(const.TASK_PLAN_PERCENT_SCHEDULE)
    
    if response.status_code == 200:
        data = response.json()
        task_name = data.get("task_name", "unknown")
        percent = data.get("percent", 0)
        time_left = data.get("time_left", 0)
        source_day = data.get("source_day", "")
        
        msg = f"Next Task: {task_name}\nPlan: {percent}%\nTime Left: {time_left} min"
        if source_day:
            msg += f"\nRollover from: {source_day}"
        return msg
    elif response.status_code == 404:
        return "No tasks available in current schedule."
    else:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))

def _minutes(m: int) -> str:
    if m < 60:
        return f"{m}м"
    return f"{m // 60}ч" if m % 60 == 0 else f"{m // 60}ч {m % 60}м"


def FormatWeeklyDigest(d: dict) -> str:
    """Formats GET /api/v1/stats/weekly/digest as a plain-text message."""
    lines = [f"📊 Итоги недели: {d.get('week_start_date', '')} — {d.get('week_end_date', '')}"]
    total_done = d.get("total_done", 0)
    if not total_done:
        return lines[0] + "\nЗа эту неделю записей нет."

    total_planned = d.get("total_planned", 0)
    plan_percent = total_done * 100 // total_planned if total_planned else 0
    lines.append(f"Всего: {_minutes(total_done)} из {_minutes(total_planned)} по плану ({plan_percent}%)")

    lines.append("\nРоли:")
    for r in d.get("roles") or []:
        lines.append(f"• {r['role']}: {_minutes(r['done'])} из {_minutes(r['planned'])} · {r['share_percent']}% времени")

    strict = d.get("strict") or []
    if strict:
        lines.append("\nСтрогие задачи:")
        for t in strict:
            lines.append(f"• {t['name']}: {_minutes(t['done'])} из {_minutes(t['planned'])} ({t['plan_percent']}%)")

    free = [t for t in d.get("free") or [] if t["done"] > 0]
    if free:
        lines.append(f"\nСвободное время ({_minutes(d.get('free_done', 0))}):")
        for t in free:
            lines.append(f"• {t['name']}: {_minutes(t['done'])} · {t['share_percent']}% · план {_minutes(t['planned'])}")

    over_plan = d.get("over_plan") or []
    untouched = d.get("untouched") or []
    unscheduled = d.get("unscheduled") or []
    if over_plan or untouched or unscheduled:
        lines.append("\nВыбор против расписания:")
        for t in over_plan:
            lines.append(f"• сверх плана — {t['name']}: +{_minutes(t['delta'])}")
        for t in untouched:
            lines.append(f"• не начато — {t['name']}: план {_minutes(t['planned'])}")
        for t in unscheduled:
            lines.append(f"• без расписания — {t['name']}: {_minutes(t['done'])}")

    busiest = d.get("busiest_day")
    if busiest:
        lines.append(f"\nСамый нагруженный день: {busiest['day']} — {_minutes(busiest['total_done'])}")
    return "\n".join(lines)


def GetWeeklyDigest(week: str = "current") -> str:
    response = requests.get(const.WEEKLY_DIGEST_URI, params={"week": week})
    if response.status_code != 200:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))
    return FormatWeeklyDigest(response.json())