from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .callback import task_callback

# Persistent buttons under the input field; their texts arrive as plain messages.
MAIN_TASKS = "▶️ Задачи"
MAIN_NOW = "⏯ Сейчас"
MAIN_TODAY = "📊 Сегодня"
MAIN_DEBT = "💳 Долг"
MAIN_BUTTONS = (MAIN_TASKS, MAIN_NOW, MAIN_TODAY, MAIN_DEBT)

START_DURATIONS = (15, 30, 45, 60)
TASKS_PER_ROW = 2
MAX_DEBT_BUTTONS = 8

# Callback prefixes. A task name goes through task_callback (64-byte limit).
TASK_CARD_PREFIX = "q_task"   # q_task:<task>         → duration card
GO_PREFIX = "q_go"            # q_go:<task>:<min>     → start for <min>
DEBT_PREFIX = "q_debt"        # q_debt:<task>:<min>   → start for <min>, all of it pays the debt
TASKS_DATA = "q_list"
TODAY_DATA = "q_today"
DEBTS_DATA = "q_debts"
BREAK_MENU_DATA = "brk_menu"  # handled in handlers/breaks.py
WEEK_DIGEST_DATA = "week_digest"  # handled in handlers/statistic.py


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MAIN_TASKS), KeyboardButton(text=MAIN_NOW)],
            [KeyboardButton(text=MAIN_TODAY), KeyboardButton(text=MAIN_DEBT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _task_label(name: str, remaining: int, debt: int) -> str:
    label = f"{name} · {remaining}м" if remaining > 0 else f"✓ {name}"
    if debt > 0:
        label += f" · 💳{debt}"
    return label


def get_task_grid_keyboard(tasks: list[tuple[str, int]], debt_by_task: dict[str, int]) -> InlineKeyboardMarkup:
    """`tasks` is [(name, minutes left today)] in display order."""
    buttons = [
        InlineKeyboardButton(
            text=_task_label(name, remaining, debt_by_task.get(name, 0)),
            callback_data=task_callback(TASK_CARD_PREFIX, name),
        )
        for name, remaining in tasks
    ]
    rows = [buttons[i:i + TASKS_PER_ROW] for i in range(0, len(buttons), TASKS_PER_ROW)]
    rows.append([
        InlineKeyboardButton(text="☕️ Перерыв", callback_data=BREAK_MENU_DATA),
        InlineKeyboardButton(text="💳 Долг", callback_data=DEBTS_DATA),
        InlineKeyboardButton(text="📊 Сегодня", callback_data=TODAY_DATA),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_task_card_keyboard(name: str, remaining: int, debt: int) -> InlineKeyboardMarkup:
    rows = []
    if remaining > 0:
        rows.append([InlineKeyboardButton(
            text=f"▶️ Остаток {remaining}м",
            callback_data=task_callback(GO_PREFIX, name, f":{remaining}"),
        )])
    rows.append([
        InlineKeyboardButton(text=f"{m}м", callback_data=task_callback(GO_PREFIX, name, f":{m}"))
        for m in START_DURATIONS
    ])
    if debt > 0:
        rows.append([InlineKeyboardButton(
            text=f"💳 Закрыть долг {debt}м",
            callback_data=task_callback(DEBT_PREFIX, name, f":{debt}"),
        )])
    rows.append([InlineKeyboardButton(text="« Задачи", callback_data=TASKS_DATA)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_debt_keyboard(debt_by_task: dict[str, int]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"▶️ {name} · закрыть {minutes}м",
            callback_data=task_callback(DEBT_PREFIX, name, f":{minutes}"),
        )]
        for name, minutes in list(debt_by_task.items())[:MAX_DEBT_BUTTONS]
    ]
    rows.append([InlineKeyboardButton(text="▶️ Задачи", callback_data=TASKS_DATA)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_today_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=TODAY_DATA),
            InlineKeyboardButton(text="📅 Неделя", callback_data=WEEK_DIGEST_DATA),
        ],
        [
            InlineKeyboardButton(text="▶️ Задачи", callback_data=TASKS_DATA),
            InlineKeyboardButton(text="💳 Долг", callback_data=DEBTS_DATA),
        ],
    ])


def get_idle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Задачи", callback_data=TASKS_DATA)],
    ])
