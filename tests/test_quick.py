import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from aiogram.types import ReplyKeyboardMarkup

from handlers import quick as quick_handler
from keyboards import quick as kb
from keyboards.callback import task_hash
from tracker import const, debt as debt_api, errors, stats, timer

TODAY = [
    {"name": "work", "role": "work", "time_duration": 120, "time_done": 120, "priority": 1},
    {"name": "video", "role": "rest", "time_duration": 30, "time_done": 10, "priority": 5},
    {"name": "english", "role": "learn", "time_duration": 60, "time_done": 0, "priority": 2},
]
DEBT = {
    "total_minutes": 55,
    "items": [
        {"task_name": "video", "role": "rest", "day": "monday", "date": "9 November 2026", "remaining": 25},
        {"task_name": "telegram", "role": "rest", "day": "monday", "date": "9 November 2026", "remaining": 15},
        {"task_name": "video", "role": "rest", "day": "tuesday", "date": "10 November 2026", "remaining": 15},
    ],
    "oldest_day": "monday",
    "today_remaining": 80,
    "days": [
        {"day": "monday", "date": "", "planned": 300, "remaining": 40, "status": "partial"},
        {"day": "tuesday", "date": "", "planned": 300, "remaining": 15, "status": "partial"},
        {"day": "wednesday", "date": "", "planned": 300, "remaining": 0, "status": "closed"},
        {"day": "thursday", "date": "", "planned": 300, "remaining": 80, "status": "today"},
        {"day": "friday", "date": "", "planned": 300, "remaining": 300, "status": "future"},
    ],
}
LONG_TASK = "очень_длинная_задача_" * 4


def _data(markup):
    return [[b.callback_data for b in row] for row in markup.inline_keyboard]


def _texts(markup):
    return [[b.text for b in row] for row in markup.inline_keyboard]


def _callback(data):
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    return callback


def _message(text):
    message = MagicMock()
    message.text = text
    message.from_user.id = const.ADMIN_ID
    message.answer = AsyncMock()
    return message


# --- tracker layer ---


def test_get_debt_unwraps_data():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"status": "success", "data": DEBT}))
        assert debt_api.GetDebt() == DEBT
        mock_get.assert_called_once_with(const.DEBT_URI)


def test_debt_by_task_sums_days_in_server_order():
    assert debt_api.DebtByTask(DEBT) == {"video": 40, "telegram": 15}
    assert list(debt_api.DebtByTask(DEBT)) == ["video", "telegram"]


def test_format_debt():
    text = debt_api.FormatDebt(DEBT)
    assert "💳 Долг прошлых дней: 55м" in text
    assert "• video — 40м (Пн 25, Вт 15)" in text
    assert "• telegram — 15м (Пн 15)" in text
    assert "Пн🟡 Вт🟡 Ср✅ Чт📍 Пт·" in text
    assert "Сегодня осталось: 1ч 20м" in text


def test_format_debt_empty():
    assert debt_api.FormatDebt({"total_minutes": 0, "items": [], "days": []}).startswith("💳 Долга нет")


def test_get_dashboard_state_url():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"today_tasks": []}))
        assert stats.GetDashboardState() == {"today_tasks": []}
        mock_get.assert_called_once_with(const.DASHBOARD_STATE_URI)


def test_get_task_list_reads_dashboard_state():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"today_tasks": TODAY, "total_planned": 210}))
        assert stats.GetTaskList() == TODAY
        mock_get.assert_called_once_with(const.DASHBOARD_STATE_URI)
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"today_tasks": None}))
        assert stats.GetTaskList() == []
    with patch("requests.get", return_value=MagicMock(status_code=500)):
        try:
            stats.GetTaskList()
        except errors.InvalidStatusCode:
            return
    assert False, "expected InvalidStatusCode"


def test_format_today():
    state = {
        "running_task": {"task_name": "video", "is_running": False, "accumulated": 12, "target_duration": 30},
        "today_tasks": TODAY,
        "total_planned": 210,
        "total_done": 130,
        "completion_pct": 61,
    }
    text = stats.FormatToday(state, debt_total=55)
    lines = text.split("\n")
    assert lines[0] == "📊 Сегодня: 2ч 10м из 3ч 30м (61%)"
    assert lines[1] == "▓▓▓▓▓▓░░░░"
    assert "⏸ На паузе: video — 12 из 30м" in text
    # Unfinished tasks first, finished ones last.
    assert text.index("• video: 10/30м — осталось 20м") < text.index("• english: 0/60м — осталось 60м") < text.index("✅ work: 120/120м")
    assert "💳 Долг прошлых дней: 55м" in text


def test_format_today_without_schedule():
    text = stats.FormatToday({"today_tasks": [], "total_planned": 0, "total_done": 0, "completion_pct": 0})
    assert "ничего нет" in text
    assert "Долг" not in text


def test_start_target():
    with patch("tracker.stats.GetTaskList", return_value=TODAY):
        assert stats.StartTarget("video") == 20
        assert stats.StartTarget("work") == stats.DEFAULT_START_MINUTES  # finished today
        assert stats.StartTarget("games") == stats.DEFAULT_START_MINUTES  # not scheduled today
    with patch("tracker.stats.GetTaskList", side_effect=Exception("down")):
        assert stats.StartTarget("video") == stats.DEFAULT_START_MINUTES


def test_timer_start_sends_debt_share():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        timer.TimerStart("video", target_duration=40, debt_share=100)
        mock_post.assert_called_once_with(
            const.TIMER_RUN_START,
            json={"task_name": "video", "target_duration": 40, "debt_share": 100},
        )


def test_elapsed_seconds_of_paused_task():
    assert timer.ElapsedSeconds({"accumulated": 3, "is_running": False}) == 180


# --- keyboards ---


def test_main_keyboard_is_persistent():
    markup = kb.get_main_keyboard()
    assert isinstance(markup, ReplyKeyboardMarkup)
    assert markup.is_persistent and markup.resize_keyboard
    assert [[b.text for b in row] for row in markup.keyboard] == [
        [kb.MAIN_TASKS, kb.MAIN_NOW],
        [kb.MAIN_TODAY, kb.MAIN_DEBT],
    ]


def test_collect_tasks_order():
    tasks = quick_handler.collect_tasks(TODAY, debt_api.DebtByTask(DEBT))
    assert tasks == [("video", 20), ("english", 60), ("telegram", 0), ("work", 0)]


def test_task_grid_keyboard():
    tasks = quick_handler.collect_tasks(TODAY, debt_api.DebtByTask(DEBT))
    markup = kb.get_task_grid_keyboard(tasks, debt_api.DebtByTask(DEBT))
    assert _texts(markup)[:2] == [
        ["video · 20м · 💳40", "english · 60м"],
        ["✓ telegram · 💳15", "✓ work"],
    ]
    assert _data(markup) == [
        ["q_task:video", "q_task:english"],
        ["q_task:telegram", "q_task:work"],
        ["brk_menu", "q_debts", "q_today"],
    ]


def test_task_card_keyboard_with_remaining_and_debt():
    markup = kb.get_task_card_keyboard("video", remaining=20, debt=40)
    assert _data(markup) == [
        ["q_go:video:20"],
        ["q_go:video:15", "q_go:video:30", "q_go:video:45", "q_go:video:60"],
        ["q_debt:video:40"],
        ["q_share:video:60-25", "q_share:video:60-50", "q_share:video:60-75"],
        ["q_list"],
    ]
    assert markup.inline_keyboard[2][0].text == "💳 Закрыть долг 40м"
    assert _texts(markup)[3] == ["💳 25%", "💳 50%", "💳 75%"]


def test_task_card_keyboard_debt_without_remaining_has_no_share_row():
    markup = kb.get_task_card_keyboard("video", remaining=0, debt=40)
    assert not any(d.startswith("q_share") for row in _data(markup) for d in row)


def test_task_card_keyboard_without_remaining_or_debt():
    markup = kb.get_task_card_keyboard("work", remaining=0, debt=0)
    assert _data(markup) == [
        ["q_go:work:15", "q_go:work:30", "q_go:work:45", "q_go:work:60"],
        ["q_list"],
    ]


def test_quick_keyboards_hash_long_names():
    for markup in (
        kb.get_task_grid_keyboard([(LONG_TASK, 10)], {LONG_TASK: 30}),
        kb.get_task_card_keyboard(LONG_TASK, remaining=10, debt=30),
        kb.get_debt_keyboard({LONG_TASK: 30}),
    ):
        for row in markup.inline_keyboard:
            for button in row:
                assert len(button.callback_data.encode("utf-8")) <= 64
    assert kb.get_task_card_keyboard(LONG_TASK, 10, 30).inline_keyboard[2][0].callback_data == f"q_debt:#{task_hash(LONG_TASK)}:30"


def test_debt_keyboard():
    markup = kb.get_debt_keyboard(debt_api.DebtByTask(DEBT))
    assert _data(markup) == [["q_debt:video:40"], ["q_debt:telegram:15"], ["q_list"]]


# --- text parsing ---


NAMES = ["video", "telegram", "home_task", "Deep Work"]


def test_parse_quick_text():
    assert quick_handler.parse_quick_text("video", NAMES) == ("video", 0, 0)
    assert quick_handler.parse_quick_text("Video 30", NAMES) == ("video", 30, 0)
    assert quick_handler.parse_quick_text("video 30м", NAMES) == ("video", 30, 0)
    assert quick_handler.parse_quick_text("video долг", NAMES) == ("video", 0, 100)
    assert quick_handler.parse_quick_text("video в долг", NAMES) == ("video", 0, 100)
    assert quick_handler.parse_quick_text("video 20 долг", NAMES) == ("video", 20, 100)
    assert quick_handler.parse_quick_text("video долг 20", NAMES) == ("video", 20, 100)
    assert quick_handler.parse_quick_text("deep work 45", NAMES) == ("Deep Work", 45, 0)


def test_parse_quick_text_share():
    assert quick_handler.parse_quick_text("video 60 50%", NAMES) == ("video", 60, 50)
    assert quick_handler.parse_quick_text("video 25% 40", NAMES) == ("video", 40, 25)
    assert quick_handler.parse_quick_text("video 50%", NAMES) == ("video", 0, 50)
    assert quick_handler.parse_quick_text("video 0%", NAMES) is None
    assert quick_handler.parse_quick_text("video 150%", NAMES) is None


def test_parse_quick_text_unknown():
    assert quick_handler.parse_quick_text("hello there", NAMES) is None
    assert quick_handler.parse_quick_text("30", NAMES) is None
    assert quick_handler.parse_quick_text("", NAMES) is None
    assert quick_handler.parse_quick_text("video 0", NAMES) is None


# --- handlers ---


def test_main_tasks_button_clears_state_and_shows_grid():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=TODAY), \
             patch("tracker.debt.GetDebt", return_value=DEBT):
            message = _message(kb.MAIN_TASKS)
            state = MagicMock()
            state.clear = AsyncMock()
            await quick_handler.main_tasks(message, state)

            state.clear.assert_called_once()
            text = message.answer.call_args[0][0]
            markup = message.answer.call_args[1]["reply_markup"]
            assert text.startswith("▶️ Что запустить?")
            assert _data(markup)[0] == ["q_task:video", "q_task:english"]

    asyncio.run(run())


def test_task_grid_survives_debt_failure():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=TODAY), \
             patch("tracker.debt.GetDebt", side_effect=Exception("down")):
            callback = _callback("q_list")
            await quick_handler.process_tasks(callback)
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert _texts(markup)[0] == ["video · 20м", "english · 60м"]

    asyncio.run(run())


def test_task_card():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=TODAY), \
             patch("tracker.debt.GetDebt", return_value=DEBT):
            callback = _callback("q_task:video")
            await quick_handler.process_task_card(callback)

            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert "Сегодня: 10/30м — осталось 20м" in text
            assert "💳 Долг прошлых дней: 40м" in text
            assert "💳 % — запуск на 60м" in text
            assert _data(markup)[0] == ["q_go:video:20"]
            assert _data(markup)[2] == ["q_debt:video:40"]
            assert _data(markup)[3][1] == "q_share:video:60-50"

    asyncio.run(run())


def test_task_card_for_debt_only_task():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=TODAY), \
             patch("tracker.debt.GetDebt", return_value=DEBT):
            callback = _callback("q_task:telegram")
            await quick_handler.process_task_card(callback)
            text = callback.message.edit_text.call_args[0][0]
            assert "нет в расписании" in text

    asyncio.run(run())


def test_go_starts_with_duration_and_shows_remote():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'video'.") as mock_start:
            callback = _callback("q_go:video:45")
            await quick_handler.process_go(callback)

            mock_start.assert_called_once_with("video", target_duration=45, debt_share=0)
            assert callback.message.edit_text.call_args[0][0] == "▶️ video — 45 мин"
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert _data(markup) == [["t_pause:video", "t_stop:video", "t_switch"]]

    asyncio.run(run())


def test_debt_button_starts_with_full_share():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'video'.") as mock_start:
            callback = _callback("q_debt:video:40")
            await quick_handler.process_debt_start(callback)

            mock_start.assert_called_once_with("video", target_duration=40, debt_share=100)
            assert callback.message.edit_text.call_args[0][0] == "💳 video — 40 мин в счёт долга"

    asyncio.run(run())


def test_share_button_starts_with_partial_share():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'video'.") as mock_start:
            callback = _callback("q_share:video:60-25")
            await quick_handler.process_share_start(callback)

            mock_start.assert_called_once_with("video", target_duration=60, debt_share=25)
            assert callback.message.edit_text.call_args[0][0] == "▶️ video — 60 мин, 💳 25% в долг"

    asyncio.run(run())


def test_share_button_with_hashed_name():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=[]), \
             patch("tracker.debt.GetDebt", return_value={"items": [{"task_name": LONG_TASK, "remaining": 30}]}), \
             patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.timer.TimerStart", return_value="Started") as mock_start:
            callback = _callback(f"q_share:#{task_hash(LONG_TASK)}:40-75")
            await quick_handler.process_share_start(callback)
            mock_start.assert_called_once_with(LONG_TASK, target_duration=40, debt_share=75)

    asyncio.run(run())


def test_start_failure_alerts_and_keeps_message():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Failed to start timer: status code 400"):
            callback = _callback("q_go:video:30")
            await quick_handler.process_go(callback)

            assert callback.answer.call_args[1]["show_alert"] is True
            callback.message.edit_text.assert_not_called()

    asyncio.run(run())


def test_start_unresolved_hash_refuses():
    async def run():
        with patch("tracker.debt.GetDebt", return_value=DEBT), \
             patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.stats.GetTaskList", return_value=[]), \
             patch("tracker.timer.TimerStart") as mock_start:
            callback = _callback("q_debt:#0123456789ab:40")
            await quick_handler.process_debt_start(callback)

            mock_start.assert_not_called()
            assert callback.answer.call_args[1]["show_alert"] is True

    asyncio.run(run())


def test_start_resolves_hashed_debt_task():
    async def run():
        debt = {"items": [{"task_name": LONG_TASK, "day": "monday", "remaining": 30}]}
        with patch("tracker.debt.GetDebt", return_value=debt), \
             patch("tracker.timer.TimerStart", return_value="Started") as mock_start:
            callback = _callback(f"q_debt:#{task_hash(LONG_TASK)}:30")
            await quick_handler.process_debt_start(callback)
            mock_start.assert_called_once_with(LONG_TASK, target_duration=30, debt_share=100)

    asyncio.run(run())


def test_today_card():
    async def run():
        state = {"today_tasks": TODAY, "total_planned": 210, "total_done": 130, "completion_pct": 61}
        with patch("tracker.stats.GetDashboardState", return_value=state), \
             patch("tracker.debt.GetDebt", return_value=DEBT):
            message = _message(kb.MAIN_TODAY)
            fsm = MagicMock()
            fsm.clear = AsyncMock()
            await quick_handler.main_today(message, fsm)

            text = message.answer.call_args[0][0]
            markup = message.answer.call_args[1]["reply_markup"]
            assert text.startswith("📊 Сегодня")
            assert "💳 Долг прошлых дней: 55м" in text
            assert _data(markup) == [["q_today", "week_digest"], ["q_list", "q_debts"]]

    asyncio.run(run())


def test_today_refresh_not_modified_is_quiet():
    async def run():
        state = {"today_tasks": [], "total_planned": 0, "total_done": 0, "completion_pct": 0}
        with patch("tracker.stats.GetDashboardState", return_value=state), \
             patch("tracker.debt.GetDebt", return_value={}):
            callback = _callback("q_today")
            callback.message.edit_text = AsyncMock(side_effect=Exception("Bad Request: message is not modified"))
            await quick_handler.process_today(callback)
            callback.message.answer.assert_not_called()

    asyncio.run(run())


def test_debt_card():
    async def run():
        with patch("tracker.debt.GetDebt", return_value=DEBT):
            callback = _callback("q_debts")
            await quick_handler.process_debts(callback)
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert _data(markup)[0] == ["q_debt:video:40"]

    asyncio.run(run())


def test_now_when_idle():
    async def run():
        with patch("tracker.timer.TimerList", return_value=[]):
            message = _message(kb.MAIN_NOW)
            fsm = MagicMock()
            fsm.clear = AsyncMock()
            await quick_handler.main_now(message, fsm)
            assert message.answer.call_args[0][0] == "Сейчас ничего не идёт."
            assert _data(message.answer.call_args[1]["reply_markup"]) == [["q_list"]]

    asyncio.run(run())


def test_now_with_running_task_shows_remote():
    async def run():
        with patch("tracker.timer.TimerList", return_value=[{"task_name": "video", "is_running": True}]), \
             patch("tracker.timer.TimerStatus", return_value="Timer running: 'video', Elapsed: 05m 00s"):
            message = _message(kb.MAIN_NOW)
            fsm = MagicMock()
            fsm.clear = AsyncMock()
            await quick_handler.main_now(message, fsm)
            assert _data(message.answer.call_args[1]["reply_markup"]) == [["t_pause:video", "t_stop:video", "t_switch"]]

    asyncio.run(run())


def _run_text(text, today=TODAY, debt=DEBT, start_result="Started", break_options=None):
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=today), \
             patch("tracker.debt.GetDebt", return_value=debt), \
             patch("tracker.evening.get_break_options", return_value={"options": break_options or []}), \
             patch("tracker.timer.TimerStart", return_value=start_result) as mock_start:
            message = _message(text)
            await quick_handler.quick_text_start(message)
            return message, mock_start
    return asyncio.run(run())


def test_text_start_uses_today_remainder():
    message, mock_start = _run_text("video")
    mock_start.assert_called_once_with("video", target_duration=20, debt_share=0)
    assert message.answer.call_args[0][0] == "▶️ video — 20 мин"


def test_text_start_with_minutes():
    _, mock_start = _run_text("english 25")
    mock_start.assert_called_once_with("english", target_duration=25, debt_share=0)


def test_text_debt_closes_whole_debt():
    message, mock_start = _run_text("video долг")
    mock_start.assert_called_once_with("video", target_duration=40, debt_share=100)
    assert message.answer.call_args[0][0] == "💳 video — 40 мин в счёт долга"


def test_text_share_with_minutes():
    message, mock_start = _run_text("video 60 50%")
    mock_start.assert_called_once_with("video", target_duration=60, debt_share=50)
    assert message.answer.call_args[0][0] == "▶️ video — 60 мин, 💳 50% в долг"


def test_text_share_without_minutes_covers_remainder_and_debt():
    _, mock_start = _run_text("video 50%")
    mock_start.assert_called_once_with("video", target_duration=60, debt_share=50)


def test_text_share_without_debt():
    message, mock_start = _run_text("english 50%")
    mock_start.assert_not_called()
    assert message.answer.call_args[0][0] == "У english нет долга."


def test_text_debt_without_debt():
    message, mock_start = _run_text("english долг")
    mock_start.assert_not_called()
    assert message.answer.call_args[0][0] == "У english нет долга."


def test_text_start_task_from_break_options():
    _, mock_start = _run_text("games 15", break_options=[{"task_name": "games"}])
    mock_start.assert_called_once_with("games", target_duration=15, debt_share=0)


def test_text_unknown_task():
    message, mock_start = _run_text("привет")
    mock_start.assert_not_called()
    assert message.answer.call_args[0][0].startswith("Не нашёл задачу «привет»")


def test_text_start_failure_has_no_remote():
    message, _ = _run_text("video 10", start_result="Failed to start timer: status code 500")
    assert message.answer.call_args[0][0] == "Failed to start timer: status code 500"
    assert message.answer.call_args[1]["reply_markup"] is None
