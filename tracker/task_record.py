import requests
from . import const, errors

def AddTaskRecord(message: str = "", task_name: str = "", time_done: int = 0) -> str:
    params = {}
    if message == "":
        params["task"] = task_name
        params["time"] = time_done
    else:
        for i in message.split()[1:]:
            key, value = i.split("=")
            params[key] = value
    if params.get("task") == None or params.get("task") == "":
        return "Task Not Found"
    if params.get("time") == None or params.get("time") == 0:
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


def GetTaskPlanPercent():
    response = requests.get(const.TASK_PLAN_PERCENT)
    answer_msg = response.json()
    message = f"Task Name: {answer_msg['task_name']}\nPercent: {answer_msg['percent']}\nTime Left: {answer_msg['time_left']}"

    # Check the response status code
    if response.status_code == 200:
        # Success!
        return message
    else:
        raise errors.InvalidStatusCode("GET request failed with status code: " + str(response.status_code))