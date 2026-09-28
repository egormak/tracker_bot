# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Telegram bot (aiogram v3) that is a thin client for a separate "tracker" HTTP API (`app_url` in config). It lets a single admin user record tasks, run per-task timers, manage rest minutes, and view stats/plan progress from Telegram. There are no local models or a database here — all state lives behind the tracker API; this bot only formats Telegram interactions and makes HTTP calls.

## Commands

No linter or formatter is configured — don't invent `ruff`/`black`/etc. commands. Tests use `pytest` (`pytest.ini` only sets `pythonpath = .`); `pytest` is not listed in `requirements.txt`, so install it into the venv yourself.

```bash
# Local setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config_example.yaml config.yaml   # set telegram.token and app_url
python main.py

# Tests (config.yaml must exist in the repo root — see "config" below; values are irrelevant since HTTP is mocked)
python -m pytest -q
python -m pytest tests/test_remote_timer.py::test_callback_t_pause -q   # single test

# Docker
docker build -t tracker-bot .
docker run -it --rm -v ${PWD}/config.yaml:/usr/src/app/config.yaml tracker-bot
```

Production images are published via `.github/workflows/docker-publish.yml` on push to `main`/`master` (tags `ghcr.io/egormak/tracker-bot:<date>` and `:latest`).

## Architecture

Two-layer split, mirrored 1:1 by module name:

- `handlers/` — aiogram `Router`s: Telegram-facing concerns only (commands, FSM states, inline keyboards, formatting replies). One router per domain: `begin.py` (start/help/webapp), `task_record.py`, `timer.py`, `rest.py`, `statistic.py`, `evening.py` (`/evening` focus triage: top-3 weekly-deficit tasks, `eve_*` callbacks), `ramp.py` (`/ramp` warm-up ramp status/reset). `handlers/task_callback.py` is a shared helper, not a router.
- `tracker/` — plain functions that call the external tracker HTTP API via `requests` and return already-formatted strings (or raise). One module per domain, matching `handlers/` (`stats.py` ↔ `statistic.py`), plus `evening.py`, `const.py` (all endpoint URLs, built from `config.config['app_url']`), `errors.py` (`InvalidStatusCode`), and `general.py` (auth decorators). `tracker/ramp.py` is the one module that parses responses into pydantic models (`RampStatus`/`RampConfig`).
- `keyboards/` — reusable `InlineKeyboardMarkup` builders (`timer.py`, `ramp.py`) and `callback.py` (callback-data encoding). Some handlers still build keyboards inline (e.g. `handlers/evening.py::build_evening_keyboard`).
- `config/__init__.py` — loads `config.yaml` from the **current working directory** at import time into `config.config` (a dict). `tracker/const.py` reads from this at import time, so `config.yaml` must exist (and you must run from the repo root) before anything under `tracker/` is imported — this applies to tests too.
- `main.py` — builds the `Bot`/`Dispatcher`, registers each handler router via `dp.include_routers(...)` (a new router must be added there), starts polling. No webhook mode.

### Server-originated messages

The bot doesn't only answer its own commands: `tracker-server` (`internal/notify/telegram`) sends messages directly to the admin chat with inline buttons — running-timer remote (`t_pause:`/`t_stop:`) and the session-completion push card (`t_start:`, `t_extend:<task>:<min>`, `t_rest:<min>`, `t_evening_top3`). The `t_*` callback handlers in `handlers/timer.py` must keep accepting exactly what the server emits; `keyboards/timer.py` mirrors the same layouts for bot-sent messages. Changing a `t_*` prefix or payload shape requires a matching change in `tracker-server`.

Handler → tracker call convention: handlers import the sibling `tracker` module and call its functions directly (e.g. `handlers/timer.py` calls `tracker.timer.TimerStart(...)`); business logic and URL construction never live in `handlers/`.

### Auth

Every command is gated to a single admin via decorators in `tracker/general.py`, checked against `tracker/const.ADMIN_ID` (hardcoded, not in `config.yaml`):
- `@general.telegram_auth` — for plain `async def handler(message)`.
- `@general.telegram_auth_with_state` — for FSM handlers with signature `(message, state)`.

Callback-query handlers and mid-FSM message handlers are generally *not* re-wrapped with an auth decorator (the state was only reachable after an authorized entry point), so don't add auth checks there — follow the existing pattern per handler file.

### FSM pattern (multi-step commands)

Commands that need an argument (task name, minutes) support two paths in one handler:
1. Argument given inline on the command line (e.g. `/restadd 30`) → resolve immediately, no state.
2. No argument → show an inline keyboard or prompt, `state.set_state(...)`, then a second handler (registered for that state, or a `callback_query` matching a `"prefix:"` data string) completes the action and calls `state.clear()`. Build task-name callback data with `keyboards/callback.py::task_callback` (never an f-string — Telegram's 64-byte limit) and resolve it with `handlers/task_callback.py::resolve_task_token`.

When adding a new stateful command, follow this same shape (see `handlers/timer.py::command_timer_start` / `process_timer_start`, or `handlers/rest.py::command_rest_add` / `process_rest_add`) rather than introducing a different state-management approach.

### Tracker API conventions

- All HTTP calls use synchronous `requests` inside `async def` handlers/tracker functions — this blocks the event loop; it's an existing, accepted tradeoff in this codebase, not something to "fix" incidentally while doing unrelated work.
- Endpoints are centralized in `tracker/const.py`; add new endpoints there rather than building URLs inline in a tracker module.
- Response shape is inconsistent across endpoints — some return the payload directly (e.g. `stats.GetTaskList`), others wrap it as `{"status": "success", "data": {...}}` (e.g. `timer.TimerStatus`, `timer.TimerList`). Check the existing function for the endpoint you're touching rather than assuming a shape.
- Non-200 responses either return a formatted error string or raise `tracker.errors.InvalidStatusCode` — callers in `handlers/` must be ready for either (see the `try/except errors.InvalidStatusCode` pattern in `handlers/statistic.py` and `handlers/task_record.py`).
- Rest-time units: `AddRest` and `SpendRest` send raw minutes in `{"rest_time": minutes}`; `GetRest` returns hundredths of a minute, converted as `minutes = data["rest_time"] / 100`.

### Tests

Tests in `tests/` never hit the network or Telegram, and follow two patterns:
- `tracker/` functions: patch `requests.get`/`requests.post` and assert both the returned string and the exact URL (`const.*`) and JSON payload sent.
- `handlers/`: patch the `tracker.<module>.<Function>` being called (and `tracker.const.ADMIN_ID` for auth-decorated commands), build the `Message`/`CallbackQuery` from `MagicMock` with `AsyncMock` for `answer`/`edit_text`, then assert the reply text and the `reply_markup` button texts and `callback_data`.

There's no `pytest-asyncio`. Async handlers run inside a sync test through an inner `async def run()` wrapped in `asyncio.run(run())`, so keep using that pattern.
