# tracker_bot

A Telegram bot designed to interface with the tracker system. It allows users to record tasks, manage rest time, and control timers directly from Telegram.

## Project Overview

- **Technologies**: Python 3.11+, aiogram v3, Pydantic, Requests.
- **Architecture**:
  - `main.py`: Entry point, initializes the bot and registers routers.
  - `handlers/`: Modular command handlers using aiogram Routers.
    - `task_record.py`, `timer.py`, `rest.py`, `statistic.py`, `begin.py`.
  - `tracker/`: Business logic and API interaction layer.
    - `task_record.py`, `timer.py`, `rest.py`, `stats.py`.
  - `config/`: Configuration loading from `config.yaml`.

## Building and Running

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from @BotFather)

### Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config_example.yaml config.yaml # Configure token and API URL
python main.py
```

### Docker
```bash
docker build -t tracker-bot .
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml tracker-bot
```

## Key Commands (Telegram)
- `/start`: Initial bot greeting and help.
- Recording: Select task and enter minutes done.
- Timer: Start, stop, pause, resume, or check status of the active timer.
- Rest: Add, spend, or check available rest minutes.
- Statistics: View today's summary.

## Development Conventions

- **FSM**: Use aiogram's Finite State Machine for multi-step interactions.
- **API Interaction**: Keep all API calls in the `tracker/` package.
- **Authentication**: Use `@general.telegram_auth` decorators to restrict access to the `ADMIN_ID` configured in `config.yaml`.
- **Async/Sync**: The bot lifecycle is asynchronous (`aiogram`), but API calls currently use the synchronous `requests` library.
