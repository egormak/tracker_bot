import requests
from . import const

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

if __name__ == "__main__":
    GetStats()