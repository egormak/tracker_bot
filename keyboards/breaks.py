from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .callback import task_callback

# Must stay in sync with tracker-server's internal/notify/telegram breakSelectorRows,
# which puts the same buttons on the session-completion card.
BREAK_DURATIONS = (15, 20, 30)
DEFAULT_BREAK_MINUTES = 15
MAX_MOOD_OPTIONS = 6
BUTTONS_PER_ROW = 3

START_PREFIX = "t_brk"
DURATION_PREFIX = "t_brkdur"


def _duration_label(minutes: int, selected: int) -> str:
    return f"✓ {minutes}м" if minutes == selected else f"{minutes}м"


def get_break_selector_rows(options: list[dict], minutes: int = DEFAULT_BREAK_MINUTES) -> list[list[InlineKeyboardButton]]:
    """Rows of the break selector: the least-done task of the week, the mood carousel
    and the duration switch. `options` come from GET /api/v1/mode/break-options, least done first."""
    names = [(o.get("task_name", ""), o.get("weekly_done", 0)) for o in options]
    names = [(name, done) for name, done in names if name]
    if not names:
        return []

    suffix = f":{minutes}"
    variety_name, variety_done = names[0]
    rows = [[
        InlineKeyboardButton(
            text=f"🎲 {variety_name} · за неделю {variety_done}м",
            callback_data=task_callback(START_PREFIX, variety_name, suffix),
        )
    ]]

    mood = names[1:1 + MAX_MOOD_OPTIONS]
    for start in range(0, len(mood), BUTTONS_PER_ROW):
        rows.append([
            InlineKeyboardButton(text=name, callback_data=task_callback(START_PREFIX, name, suffix))
            for name, _ in mood[start:start + BUTTONS_PER_ROW]
        ])

    rows.append([
        InlineKeyboardButton(text=_duration_label(m, minutes), callback_data=f"{DURATION_PREFIX}:{m}")
        for m in BREAK_DURATIONS
    ])
    return rows


def get_break_selector_keyboard(options: list[dict], minutes: int = DEFAULT_BREAK_MINUTES) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=get_break_selector_rows(options, minutes))


def with_break_duration(markup: InlineKeyboardMarkup, minutes: int) -> InlineKeyboardMarkup:
    """Returns a copy of `markup` whose break buttons start `minutes`-long sessions.
    Other buttons are kept, so it works on the server-built completion card too."""
    rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for button in row:
            data = button.callback_data or ""
            if data.startswith(f"{START_PREFIX}:"):
                # The task part may contain ':'; the duration is always the last segment.
                head, _ = data.rsplit(":", 1)
                button = button.model_copy(update={"callback_data": f"{head}:{minutes}"})
            elif data.startswith(f"{DURATION_PREFIX}:"):
                value = data.split(":", 1)[1]
                if value.isdigit():
                    button = button.model_copy(update={"text": _duration_label(int(value), minutes)})
            new_row.append(button)
        rows.append(new_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
