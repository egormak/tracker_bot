import requests
from . import const, errors

def AddRest(time_minutes: int) -> str:
    data = {"minutes": time_minutes}
    response = requests.post(const.REST_ADD_URI, json=data)

    if response.status_code == 200:
        return f"Added {time_minutes} minutes of rest."
    else:
        return f"Failed to add rest with status code: {response.status_code}"

def SpendRest(time_minutes: int) -> str:
    data = {"minutes": time_minutes}
    response = requests.post(const.REST_SPEND_URI, json=data)

    if response.status_code == 200:
        return f"Spent {time_minutes} minutes of rest."
    else:
        return f"Failed to spend rest with status code: {response.status_code}"

def GetRest() -> str:
    response = requests.get(const.REST_GET_URI)

    if response.status_code == 200:
        try:
            data = response.json()
            minutes = data.get("rest_time", 0) / 100
            return f"Available rest time: {minutes} minutes."
        except Exception:
            return "Failed to parse available rest response."
    else:
        raise errors.InvalidStatusCode(f"GET request failed with status code: {response.status_code}")
