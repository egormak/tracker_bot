# tracker_bot

A Telegram bot client (aiogram v3) designed to interface with `tracker-server`. It allows a single admin user to record tasks, manage rest time, control task timers, view statistics, run warm-up ramps, and execute evening focus triage directly from Telegram.

## Project Overview

- **Technologies**: Python 3.10+, aiogram v3, Pydantic, Requests, Pytest.
- **Bot Nature**: Stateless thin client. All state (tasks, active timers, schedules, ramp progress, rest balances) lives in `tracker-server`. The bot only handles Telegram UI, FSM, and HTTP API calls.

## Architecture

The project follows a strict two-layer separation:

- `handlers/`: aiogram `Router`s dealing exclusively with Telegram-facing concerns (command filters, FSM states, callbacks, inline keyboards, reply formatting).
  - `begin.py`: `/start`, `/help`, `/webapp` mini-app button.
  - `task_record.py`: `/taskrecordadd` (record completed task time), `/task_plan_percent` (progress towards planned duration), FSM flow.
  - `timer.py`: `/timer_start`, `/timer_stop`, `/timer_pause`, `/timer_resume`, `/timer_status`, and server-originated remote timer callbacks (`t_*`).
  - `rest.py`: `/restadd`, `/restspend`, `/restget` for managing rest minutes.
  - `statistic.py`: `/stats` (daily stats), `/tasklist` (summary of daily tasks and remaining time), `/nexttask` (schedule-based recommendation).
  - `evening.py`: `/evening` (Evening Focus Mode 2.0 triage: top-3 weekly deficit tasks, sprint combos, skips, duration adjustments, `eve_*` callbacks).
  - `ramp.py`: `/ramp` (Warm-Up Ramp Ladder status and `ramp:reset` callback).
  - `task_callback.py`: Shared utility (not a router) for resolving task names from tokens and splitting payloads containing colons.
- `tracker/`: API communication layer using synchronous `requests`, returning formatted strings or parsed data:
  - `const.py`: All endpoint URLs constructed from `config['app_url']`, plus hardcoded `ADMIN_ID`.
  - `general.py`: Auth decorators (`@telegram_auth`, `@telegram_auth_with_state`).
  - `errors.py`: Exception classes (`InvalidStatusCode`).
  - `task_record.py`: Add task records, query plan completion percentage.
  - `timer.py`: Timer lifecycle (start, stop, pause, resume, adjust, status, list, raw status).
  - `rest.py`: Add, spend, and fetch rest time.
  - `stats.py`: Daily records, task lists, and next schedule task.
  - `evening.py`: Fetch evening focus candidates and skip evening tasks.
  - `ramp.py`: Fetch and reset warm-up ramp, parsed into Pydantic models (`RampStatus`, `RampConfig`).
- `keyboards/`: Reusable inline keyboard builders and callback utilities:
  - `timer.py`: `get_running_timer_keyboard`, `get_paused_timer_keyboard`, `get_completion_push_card_keyboard`.
  - `ramp.py`: `get_ramp_keyboard` (`ramp:reset`).
  - `callback.py`: `task_callback` utility ensuring callback payloads fit Telegram's 64-byte limit.
- `config/`: Loads `config.yaml` from the current working directory at import time into `config.config` (dict).
- `main.py`: Entry point, initializes `Bot` and `Dispatcher`, registers all routers with `dp.include_routers(...)`, and runs the polling loop (no webhooks).

## Building, Running, and Testing

### Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config_example.yaml config.yaml   # Set telegram.token and app_url
python main.py
```

### Running Tests
Tests use `pytest` with `pytest.ini` (`pythonpath = .`). Note that `config.yaml` must exist in the working directory before running tests because `tracker/const.py` loads it upon import (actual values do not matter since HTTP calls are mocked).

```bash
# Run all tests
python -m pytest -q

# Run single test
python -m pytest tests/test_remote_timer.py::test_callback_t_pause -q
```

### Docker
```bash
# Local build and run
docker build -t tracker-bot .
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml tracker-bot

# Production CI/CD
# Images are published via GitHub Actions on push to main/master:
# ghcr.io/egormak/tracker-bot:<date> and :latest
```

### Code Style
No linter or code formatter (like ruff or black) is configured in the repository; avoid running or introducing formatting commands unless explicitly asked.

## Key Commands (Telegram)

- **General**:
  - `/start`: Initial greeting.
  - `/help`: Show command list.
  - `/webapp`: Mini WebApp button (`https://tracker.makegorka.com/`).
- **Task & Schedule Management**:
  - `/taskrecordadd [task] [minutes]`: Record completed task time (supports inline args or interactive FSM selection).
  - `/tasklist`: View today's tasks, time done, and remaining time.
  - `/nexttask`: Get the next recommended task based on schedule.
  - `/task_plan_percent`: Current plan completion percentage.
- **Focus & Ramp Modes**:
  - `/evening`: Launch Evening Focus Mode 2.0 triage (top-3 weekly-deficit tasks, sprint timer, combos).
  - `/ramp`: View Warm-Up Ramp Ladder status and reset to 1 min step.
- **Timer Management**:
  - `/timer_start [task_name]`: Start a timer for a task (inline argument or interactive task picker).
  - `/timer_stop [task_name]`: Stop the active timer (immediate if 1 timer, picker if multiple).
  - `/timer_pause [task_name]`: Pause the running timer.
  - `/timer_resume [task_name]`: Resume the paused timer.
  - `/timer_status [task_name]`: View active timer status with interactive control buttons.
- **Rest Management**:
  - `/restadd [minutes]`: Add rest time.
  - `/restspend [minutes]`: Spend rest time.
  - `/restget`: View available rest balance.

## Server-Originated Messages & Callback Contract

The bot does not only handle user-initiated commands. `tracker-server` (`internal/notify/telegram`) sends direct messages to the admin chat with inline buttons:
- **Running Timer Remote**: `t_pause:<task>`, `t_resume:<task>`, `t_stop:<task>`, `t_switch`.
- **Session-Completion Push Card**: `t_start:<task>`, `t_extend:<task>:<min>`, `t_rest:<min>`, `t_evening_top3`.

The callback handlers in `handlers/timer.py` and keyboards in `keyboards/timer.py` must stay strictly synchronized with the prefixes and payload format emitted by `tracker-server`.

## Telegram 64-Byte Callback Limit & Token Resolution

Telegram rejects messages if any button's `callback_data` exceeds 64 UTF-8 bytes.
- Task names that would exceed this limit are truncated to `#<sha1[:12]>` using `keyboards/callback.py::task_callback`.
- When callbacks are received, `handlers/task_callback.py::resolve_task_token` resolves hashed tokens back to full task names using candidates from evening focus, active timers, or today's task list.
- Payloads with suffixes use `split_task_payload(callback_data, prefix)`, splitting from the right (`rsplit(":", 1)`) so task names containing colons are preserved.

## Development Conventions

- **Two-Layer Architecture**: Telegram UI/FSM stays in `handlers/`; HTTP calls and URL construction stay in `tracker/`. Handlers import and invoke `tracker` functions directly.
- **FSM Pattern**: Stateful commands provide dual execution paths:
  1. Inline argument (e.g. `/restadd 30` or `/timer_start coding`) executes immediately without entering state.
  2. No argument prompts with an inline keyboard or text prompt, sets FSM state, and completes on callback/message input before clearing state.
- **Authentication**: Gate entry-point handlers with `@general.telegram_auth` or `@general.telegram_auth_with_state` checking `tracker/const.ADMIN_ID`. Callbacks and intermediate FSM steps are not re-wrapped with auth decorators.
- **Centralized Endpoints**: Add all API endpoint URLs to `tracker/const.py`. Never construct endpoint URLs inside handler modules.
- **Synchronous Requests**: HTTP calls use synchronous `requests` inside async handlers. Blocking the event loop is an accepted design choice in this single-user bot.
- **API Response Shapes**: Inconsistent across endpoints; some endpoints return payload directly (e.g. `stats.GetTaskList`), while others wrap it in `{"status": "success", "data": {...}}` (e.g. `timer.TimerList`, `ramp.get_ramp_status`). Always verify the exact shape when adding or modifying calls.
- **Rest-Time Units**:
  - `AddRest` and `SpendRest` send raw minutes in `{"rest_time": minutes}`.
  - `GetRest` returns rest in units (hundredths of a minute), converted as `minutes = data["rest_time"] / 100`.
- **Testing Pattern**: Tests mock network calls and Telegram objects (`MagicMock`, `AsyncMock`). Async handler tests run synchronously inside an inner `async def run(): ...` wrapped by `asyncio.run(run())` without `pytest-asyncio`.
- **No Local State**: The bot is completely stateless; all task, timer, schedule, and rest state is managed by `tracker-server`.
