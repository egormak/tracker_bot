import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from handlers import breaks as breaks_handler
from keyboards.breaks import get_break_selector_keyboard, with_break_duration
from keyboards.callback import task_hash
from keyboards.timer import get_completion_push_card_keyboard

OPTIONS = [
    {"task_name": "movies", "role": "rest", "weekly_done": 0, "is_variety": True},
    {"task_name": "games", "role": "rest", "weekly_done": 10, "is_variety": False},
    {"task_name": "video", "role": "rest", "weekly_done": 40, "is_variety": False},
]
LONG_TASK = "очень_длинная_задача_" * 4


def _callback(data, markup=None):
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.reply_markup = markup
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.answer = AsyncMock()
    return callback


def _data(markup):
    return [[b.callback_data for b in row] for row in markup.inline_keyboard]


def test_break_selector_keyboard_layout():
    markup = get_break_selector_keyboard(OPTIONS)
    assert _data(markup) == [
        ["t_brk:movies:15"],
        ["t_brk:games:15", "t_brk:video:15"],
        ["t_brkdur:15", "t_brkdur:20", "t_brkdur:30"],
    ]
    assert markup.inline_keyboard[0][0].text == "🎲 movies · за неделю 0м"
    assert [b.text for b in markup.inline_keyboard[2]] == ["✓ 15м", "20м", "30м"]


def test_break_selector_keyboard_caps_mood_options_and_hashes_long_names():
    options = [{"task_name": LONG_TASK, "weekly_done": 0}] + [
        {"task_name": f"task{i}", "weekly_done": i} for i in range(10)
    ]
    markup = get_break_selector_keyboard(options)
    # variety + 6 mood buttons in rows of 3 + duration row
    assert [len(row) for row in markup.inline_keyboard] == [1, 3, 3, 3]
    assert markup.inline_keyboard[0][0].callback_data == f"t_brk:#{task_hash(LONG_TASK)}:15"
    for row in markup.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64


def test_break_selector_keyboard_empty_options():
    assert get_break_selector_keyboard([]).inline_keyboard == []


def test_with_break_duration_rewrites_only_break_buttons():
    card = get_completion_push_card_keyboard("work", next_task="english", break_options=OPTIONS)
    updated = with_break_duration(card, 30)
    assert _data(updated) == [
        ["t_start:english"],
        ["t_brk:movies:30"],
        ["t_brk:games:30", "t_brk:video:30"],
        ["t_brkdur:15", "t_brkdur:20", "t_brkdur:30"],
        ["t_rest:10", "t_extend:work:15"],
        ["t_evening_top3"],
    ]
    assert [b.text for b in updated.inline_keyboard[3]] == ["15м", "20м", "✓ 30м"]
    # The source keyboard is left untouched.
    assert card.inline_keyboard[1][0].callback_data == "t_brk:movies:15"


def test_with_break_duration_keeps_colons_in_task_name():
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="a:b", callback_data="t_brk:a:b:15"),
    ]])
    assert _data(with_break_duration(markup, 20)) == [["t_brk:a:b:20"]]


def test_completion_card_without_break_options_is_unchanged():
    card = get_completion_push_card_keyboard("video")
    assert _data(card) == [["t_rest:10", "t_extend:video:15"], ["t_evening_top3"]]


def test_callback_break_start_uses_selected_duration():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'games'.") as mock_start:
            callback = _callback("t_brk:games:20")
            await breaks_handler.process_break_start(callback)

            mock_start.assert_called_once_with("games", target_duration=20)
            callback.answer.assert_called_once()
            assert callback.message.edit_text.call_args[0][0] == "☕️ 'games' запущена на 20 мин."

    asyncio.run(run())


def test_callback_break_start_reports_failure():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Failed to start timer: status code 500"):
            callback = _callback("t_brk:games:15")
            await breaks_handler.process_break_start(callback)
            assert callback.message.edit_text.call_args[0][0] == "Failed to start timer: status code 500"

    asyncio.run(run())


def test_callback_break_start_resolves_hashed_name():
    async def run():
        options = {"options": [{"task_name": LONG_TASK, "weekly_done": 0}]}
        with patch("tracker.evening.get_break_options", return_value=options), \
             patch("tracker.timer.TimerStart", return_value="Started") as mock_start:
            callback = _callback(f"t_brk:#{task_hash(LONG_TASK)}:30")
            await breaks_handler.process_break_start(callback)
            mock_start.assert_called_once_with(LONG_TASK, target_duration=30)

    asyncio.run(run())


def test_callback_break_start_unresolved_hash_refuses():
    async def run():
        with patch("tracker.evening.get_break_options", return_value={"options": []}), \
             patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.stats.GetTaskList", return_value=[]), \
             patch("tracker.timer.TimerStart") as mock_start:
            callback = _callback("t_brk:#0123456789ab:15")
            await breaks_handler.process_break_start(callback)

            mock_start.assert_not_called()
            assert callback.answer.call_args[1]["show_alert"] is True
            callback.message.edit_text.assert_not_called()

    asyncio.run(run())


def test_callback_break_duration_rewrites_keyboard():
    async def run():
        callback = _callback("t_brkdur:20", markup=get_break_selector_keyboard(OPTIONS))
        await breaks_handler.process_break_duration(callback)

        markup = callback.message.edit_reply_markup.call_args[1]["reply_markup"]
        assert _data(markup)[0] == ["t_brk:movies:20"]
        assert [b.text for b in markup.inline_keyboard[2]] == ["15м", "✓ 20м", "30м"]

    asyncio.run(run())


def test_callback_break_duration_ignores_not_modified():
    async def run():
        callback = _callback("t_brkdur:15", markup=get_break_selector_keyboard(OPTIONS))
        callback.message.edit_reply_markup = AsyncMock(side_effect=Exception("Bad Request: message is not modified"))
        await breaks_handler.process_break_duration(callback)
        callback.answer.assert_called_once()

    asyncio.run(run())


def test_break_menu_renders_selector():
    async def run():
        with patch("tracker.evening.get_break_options", return_value={"options": OPTIONS}):
            callback = _callback("brk_menu")
            await breaks_handler.process_break_menu(callback)

            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert "Перерыв" in text
            assert _data(markup)[0] == ["t_brk:movies:15"]

    asyncio.run(run())


def test_break_command_without_options():
    async def run():
        with patch("tracker.evening.get_break_options", return_value={}), \
             patch("tracker.const.ADMIN_ID", 1):
            message = MagicMock()
            message.from_user.id = 1
            message.answer = AsyncMock()
            await breaks_handler.command_break_handler(message)
            assert message.answer.call_args[0][0] == "Нет задач для перерыва."
            assert message.answer.call_args[1]["reply_markup"] is None

    asyncio.run(run())
