# tracker_bot

A Telegram bot client (aiogram v3) designed to interface with `tracker-server`. It allows a single admin user to record tasks, manage rest time, control task timers, and view statistics directly from Telegram.

## Project Overview

- **Technologies**: Python 3.10+, aiogram v3, Pydantic, Requests.
- **Architecture**:
  - `main.py`: Entry point, constructs `Bot` and `Dispatcher`, registers handler routers, starts polling loop.
  - `handlers/`: Modular Telegram command routers (`begin.py`, `task_record.py`, `timer.py`, `rest.py`, `statistic.py`). Handles UI, inline keyboards, and FSM.
  - `tracker/`: API communication layer using synchronous `requests`.
    - `const.py`: Endpoint URLs constructed from `config['app_url']`.
    - `general.py`: Auth decorators (`@telegram_auth`, `@telegram_auth_with_state`).
    - `errors.py`: Exception classes (`InvalidStatusCode`).
    - `task_record.py`, `timer.py`, `rest.py`, `stats.py`: Formatted API helper functions.
  - `config/`: Configuration loading from `config.yaml` into `config.config`.

## Building and Running

### Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config_example.yaml config.yaml # Set telegram.token and app_url
python main.py
```

### Docker
```bash
docker build -t tracker-bot .
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml tracker-bot
```

## Key Commands (Telegram)

- `/start`: Initial greeting and help overview.
- `/task`: Select task and record completed minutes.
- `/timer`: Start, stop, pause, resume, or check status of active timer.
- `/rest`: Add, spend, or check available rest minutes.
- `/stats`: View today's summary statistics.

## Development Conventions

- **Two-Layer Architecture**: Keep Telegram UI/FSM in `handlers/` and API HTTP calls in `tracker/`.
- **FSM Pattern**: Stateful commands support dual execution paths: inline argument (e.g. `/restadd 30`) executes immediately; no argument prompts UI, sets FSM state, and completes on callback.
- **Authentication**: Gate entry-point handlers using `@general.telegram_auth` or `@general.telegram_auth_with_state` checking `ADMIN_ID`.
- **Centralized Endpoints**: Add new endpoint URLs to `tracker/const.py`.
- **Rest-Time Units**: Convert rest time values at boundary (`units = minutes * 100`).
- **No Local State**: The bot is completely stateless; all task and timer state resides in `tracker-server`.
