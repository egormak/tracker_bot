# tracker-bot

A Telegram bot designed to interface with a task-tracking backend API. It allows users to record tasks, manage rest time, and control timers directly from Telegram.

## Project Overview

- **Main Technology:** Python 3.11 with [aiogram v3](https://docs.aiogram.dev/en/dev-3.x/).
- **Architecture:** 
  - `main.py`: The entry point that initializes the `Dispatcher` and includes routers from the `handlers/` directory.
  - `handlers/`: Contains modular command handlers.
    - `begin.py`: Basic commands like `/start`, `/help`, and `/webapp`.
    - `task_record.py`: Recording task progress (minutes done). Uses FSM (`TaskRecord`) for interactive task/time input.
    - `timer.py`: Controls for a running timer (start, stop, pause, resume, status). Uses FSM (`TimerStartState`) to select a task when starting a timer.
    - `rest.py`: Management of "rest minutes" (add, spend, get). Uses FSM for time input.
    - `statistic.py`: View overall statistics.
  - `tracker/`: Contains the business logic and API interaction code.
    - `task_record.py`, `timer.py`, `rest.py`, `stats.py`: Individual modules for API calls using `requests`.
    - `general.py`: Authentication decorators.
    - `const.py`: Centralized API endpoints and `ADMIN_ID`.
  - `config/`: Handles configuration loading from `config.yaml`.
- **Integrations:** Interacts with a backend API (URL specified in `config.yaml`) to perform CRUD operations on tasks, rest, and timers.

## Building and Running

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from @BotFather)
- Backend API URL

### Configuration
Create a `config.yaml` file in the root directory based on `config_example.yaml`:
```yaml
telegram:
  token: "YOUR_TELEGRAM_BOT_TOKEN"
app_url: "http://your-backend-api-url"
```

### Key Commands

- **Build Docker Image:**
  ```shell
  docker build -t tracker-bot .
  ```

- **Run in Development (Docker):**
  ```shell
  docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml tracker-bot
  ```

- **Run Locally (venv):**
  ```shell
  python -m venv venv
  source venv/bin/activate  # or venv\Scripts\activate on Windows
  pip install -r requirements.txt
  python main.py
  ```

## Development Conventions

- **Command Handlers:** New bot features should be implemented as separate routers in `handlers/` and registered in `main.py`.
- **FSM (Finite State Machine):** Use `aiogram.fsm` for multi-step interactions (e.g., picking a task then entering minutes).
- **API Logic:** Keep API interaction code within the `tracker/` package.
- **Authentication:** Use the `@general.telegram_auth` or `@general.telegram_auth_with_state` decorators to restrict access to the `ADMIN_ID`.
- **Constants:** API endpoints and other global constants are defined in `tracker/const.py`.
- **Code Style:** The project uses asynchronous `aiogram` for the bot lifecycle, while the `tracker/` package uses the synchronous `requests` library for backend communication.
