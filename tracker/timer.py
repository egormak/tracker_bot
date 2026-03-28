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

def TimerStop() -> str:
    response = requests.post(const.TIMER_RUN_STOP)
    if response.status_code == 200:
        return "Timer stopped successfully."
    else:
        return f"Failed to stop timer: status code {response.status_code}"

def TimerPause() -> str:
    response = requests.post(const.TIMER_RUN_PAUSE)
    if response.status_code == 200:
        return "Timer paused."
    else:
        return f"Failed to pause timer: status code {response.status_code}"

def TimerResume() -> str:
    response = requests.post(const.TIMER_RUN_RESUME)
    if response.status_code == 200:
        return "Timer resumed."
    else:
        return f"Failed to resume timer: status code {response.status_code}"

def TimerStatus() -> str:
    response = requests.get(const.TIMER_RUN_STATUS)
    if response.status_code == 200:
        data = response.json()
        if data.get("running"):
            state = data.get("state", "unknown")
            task = data.get("task_name", "unknown task")
            elapsed = data.get("elapsed", 0)
            return f"Timer running: {task} ({state}), Elapsed: {elapsed} seconds"
        else:
            return "No timers are currently active."
    else:
        raise errors.InvalidStatusCode(f"GET request failed with status code: {response.status_code}")
