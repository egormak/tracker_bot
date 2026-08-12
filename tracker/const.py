import config

ADMIN_ID = 234872620
# URL = "http://tracker.makegorka.com:8080"
STATS_URI = f"{config.config['app_url']}/api/v1/records"
TASK_RECORD_URI = f"{config.config['app_url']}/api/v1/taskrecord"
TASK_LIST_URI = f"{config.config['app_url']}/api/v1/tasklist"
TASK_PLAN_PERCENT = f"{config.config['app_url']}/api/v1/task/plan/percent"
TASK_PLAN_PERCENT_SCHEDULE = f"{config.config['app_url']}/api/v1/task/plan/percent/schedule"

REST_ADD_URI = f"{config.config['app_url']}/api/v1/rest/add"
REST_SPEND_URI = f"{config.config['app_url']}/api/v1/rest/spend"
REST_GET_URI = f"{config.config['app_url']}/api/v1/rest/get"

TIMER_RUN_START = f"{config.config['app_url']}/api/v1/timer/run/start"
TIMER_RUN_STOP = f"{config.config['app_url']}/api/v1/timer/run/stop"
TIMER_RUN_PAUSE = f"{config.config['app_url']}/api/v1/timer/run/pause"
TIMER_RUN_RESUME = f"{config.config['app_url']}/api/v1/timer/run/resume"
TIMER_RUN_STATUS = f"{config.config['app_url']}/api/v1/timer/run/status"
TIMER_RUN_LIST = f"{config.config['app_url']}/api/v1/timer/run/list"

EVENING_FOCUS_URI = f"{config.config['app_url']}/api/v1/mode/evening-focus"
EVENING_SKIP_URI = f"{config.config['app_url']}/api/v1/mode/evening-focus/skip"
