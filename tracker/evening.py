import requests
from tracker.const import EVENING_FOCUS_URI, EVENING_SKIP_URI

def get_evening_focus(category: str = "", sprint_time: int = 20):
    params = {}
    if category:
        params["category"] = category
    if sprint_time:
        params["time"] = sprint_time

    response = requests.get(EVENING_FOCUS_URI, params=params)
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}

def skip_evening_task(task_name: str, category: str = "", sprint_time: int = 20):
    params = {}
    if category:
        params["category"] = category
    if sprint_time:
        params["time"] = sprint_time

    payload = {"task_name": task_name}
    response = requests.post(EVENING_SKIP_URI, json=payload, params=params)
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}
