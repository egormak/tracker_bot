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


if __name__ == "__main__":
    GetStats()