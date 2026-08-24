import requests
from . import const, errors

def TimerStart(task_name: str, group_name: str = "") -> str:
    data = {"task_name": task_name}
    if group_name:
        data["group_name"] = group_name

    response = requests.post(const.TIMER_RUN_START, json=data)
    
    if response.status_code == 200:
        return f"Started timer for '{task_name}'."
    else:
        return f"Failed to start timer: status code {response.status_code}"

def TimerStop(task_name: str = "") -> str:
    data = {"task_name": task_name} if task_name else {}
    response = requests.post(const.TIMER_RUN_STOP, json=data)
    if response.status_code == 200:
        return f"Timer stopped successfully for '{task_name}'." if task_name else "Timer stopped successfully."
    else:
        return f"Failed to stop timer: status code {response.status_code}"

def TimerPause(task_name: str = "") -> str:
    data = {"task_name": task_name} if task_name else {}
    response = requests.post(const.TIMER_RUN_PAUSE, json=data)
    if response.status_code == 200:
        return f"Timer paused for '{task_name}'." if task_name else "Timer paused."
    else:
        return f"Failed to pause timer: status code {response.status_code}"

def TimerResume(task_name: str = "") -> str:
    data = {"task_name": task_name} if task_name else {}
    response = requests.post(const.TIMER_RUN_RESUME, json=data)
    if response.status_code == 200:
        return f"Timer resumed for '{task_name}'." if task_name else "Timer resumed."
    else:
        return f"Failed to resume timer: status code {response.status_code}"

def TimerStatus(task_name: str = "") -> str:
    params = {"task_name": task_name} if task_name else {}
    response = requests.get(const.TIMER_RUN_STATUS, params=params)
    if response.status_code == 200:
        res_data = response.json()
        if res_data.get("status") == "success" and "data" in res_data:
            task_data = res_data["data"]
            t_name = task_data.get("task_name")
            if t_name:
                is_running = task_data.get("is_running", False)
                state = "running" if is_running else "paused"
                elapsed = task_data.get("accumulated", 0) * 60  # accumulated minutes to seconds
                
                if is_running and task_data.get("start_time"):
                    from datetime import datetime, timezone
                    try:
                        start_dt = datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00"))
                        now_dt = datetime.now(timezone.utc)
                        elapsed += int((now_dt - start_dt).total_seconds())
                    except Exception:
                        pass
                
                minutes = elapsed // 60
                seconds = elapsed % 60
                return f"Timer {state}: '{t_name}', Elapsed: {minutes:02d}m {seconds:02d}s"
            else:
                return "No timers are currently active."
        else:
            return "No timers are currently active."
    else:
        raise errors.InvalidStatusCode(f"GET request failed with status code: {response.status_code}")

def TimerList() -> list:
    response = requests.get(const.TIMER_RUN_LIST)
    if response.status_code != 200:
        raise errors.InvalidStatusCode(f"GET request failed with status code: {response.status_code}")
    try:
        res_data = response.json()
    except ValueError:
        raise errors.InvalidStatusCode("GET request returned an invalid JSON response")
    if res_data.get("status") == "success" and "data" in res_data:
        return res_data["data"]
    return []

def FilterRunning(tasks: list) -> list:
    return [t for t in tasks if t.get("is_running", False)]

def FilterPaused(tasks: list) -> list:
    return [t for t in tasks if not t.get("is_running", False)]

def TimerAdjust(task_name: str, delta_minutes: int) -> str:
    data = {"task_name": task_name, "delta_minutes": delta_minutes}
    response = requests.post(const.TIMER_RUN_ADJUST, json=data)
    if response.status_code == 200:
        sign = f"+{delta_minutes}" if delta_minutes > 0 else f"{delta_minutes}"
        return f"Adjusted timer for '{task_name}' by {sign} min."
    else:
        return f"Failed to adjust timer: status code {response.status_code}"

