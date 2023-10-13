import requests
from . import const

def AddTaskRecord(message: str) -> str:
    params = {}
    for i in message.split()[1:]:
        key, value = i.split("=")
        params[key] = value
    if params.get("task") == None:
        return "Task Not Found"
    if params.get("time") == None:
        return "Time Not Found"
    
    data = {"task_name": params.get("task"), "time_done": int(params.get("time"))}
    
    response = requests.post(const.TASK_RECORD_URI, json=data)

    # Check the response status code
    if response.status_code == 200:
        # Success!
        return "Task Added"
    else:
        # Error!
        return f"POST request failed with status code: {response.status_code}"
