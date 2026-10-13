import requests
from . import const, errors

def GetStats():
    response = requests.get(const.STATS_URI)

    if response.status_code != 200:
        message = "Can't get stats, responce code: " + str(response.status_code)
        return message

    data = response.json()
    # print(data)
    message = "Statistic Information:\n"
    for category, information in data.items():
        message += category + ": \n"
        for k,v in information.items():
            message += f"   {k}: {v}\n"
        message += "\n"
    return message

def GetTaskList() -> list[str]:
    response = requests.get(const.TASK_LIST_URI)

    # Check the response status code
    if response.status_code == 200:
        # Success!
        return response.json()
    else:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))


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


if __name__ == "__main__":
    GetStats()