import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from handlers import timer as timer_handler
from keyboards.timer import (
    get_running_timer_keyboard,
    get_paused_timer_keyboard,
    get_completion_push_card_keyboard,
)
from tracker import timer, rest, const


def test_callback_t_pause():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused for 'coding'.") as mock_pause:
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)

            mock_pause.assert_called_once_with("coding")
            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]

            assert "Timer paused for 'coding'." in text
            assert len(markup.inline_keyboard) == 1
            row = markup.inline_keyboard[0]
            assert row[0].text == "▶️ Возобновить"
            assert row[0].callback_data == "t_resume:coding"
            assert row[1].text == "⏹ Стоп"
            assert row[1].callback_data == "t_stop:coding"
            assert row[2].text == "🔄 Сменить"
            assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_callback_t_resume():
    async def run():
        with patch("tracker.timer.TimerResume", return_value="Timer resumed for 'coding'.") as mock_resume:
            callback = MagicMock()
            callback.data = "t_resume:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_resume_callback(callback)

            mock_resume.assert_called_once_with("coding")
            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]

            assert "Timer resumed for 'coding'." in text
            assert len(markup.inline_keyboard) == 1
            row = markup.inline_keyboard[0]
            assert row[0].text == "⏸ Пауза"
            assert row[0].callback_data == "t_pause:coding"
            assert row[1].text == "⏹ Стоп"
            assert row[1].callback_data == "t_stop:coding"
            assert row[2].text == "🔄 Сменить"
            assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_callback_t_stop():
    async def run():
        with patch("tracker.timer.TimerStop", return_value="Timer stopped successfully for 'coding'.") as mock_stop:
            callback = MagicMock()
            callback.data = "t_stop:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_stop_callback(callback)

            mock_stop.assert_called_once_with("coding")
            callback.answer.assert_called_once_with("⏹ Стоп")
            callback.message.edit_text.assert_called_once_with("Timer stopped successfully for 'coding'.")

    asyncio.run(run())


def test_callback_t_extend():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'coding'.") as mock_start:
            callback = MagicMock()
            callback.data = "t_extend:coding:15"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_extend_callback(callback)

            mock_start.assert_called_once_with("coding", target_duration=15)
            callback.answer.assert_called_once_with("+15 мин")
            callback.message.edit_text.assert_called_once_with("⏳ Задача 'coding' продлена на +15 мин.")

    asyncio.run(run())


def test_callback_t_extend_message_deleted_race():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'coding'."):
            callback = MagicMock()
            callback.data = "t_extend:coding:15"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=Exception("TelegramBadRequest: message to edit not found"))
            callback.answer = AsyncMock()

            # Should not raise exception
            await timer_handler.process_timer_extend_callback(callback)
            callback.answer.assert_called_once_with("+15 мин")

    asyncio.run(run())


def test_callback_t_rest_spends_minutes():
    async def run():
        with patch("tracker.rest.SpendRest", return_value="Spent 10 minutes of rest.") as mock_spend:
            callback = MagicMock()
            callback.data = "t_rest:10"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_rest_callback(callback)

            # /rest/spend takes minutes; the server converts to units itself
            mock_spend.assert_called_once_with(10)
            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once_with(
                "☕️ Списано 10 мин отдыха. Приятного перерыва!"
            )

    asyncio.run(run())


def test_callback_t_switch():
    async def run():
        fake_tasks = [
            {"name": "task_a", "time_duration": 60, "time_done": 20},
            {"name": "task_b", "time_duration": 40, "time_done": 10},
        ]
        with patch("tracker.stats.GetTaskList", return_value=fake_tasks) as mock_get_tasks:
            callback = MagicMock()
            callback.data = "t_switch"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_switch_callback(callback)

            mock_get_tasks.assert_called_once()
            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            assert "Choose task to switch:" in args[0]
            markup = kwargs["reply_markup"]
            assert len(markup.inline_keyboard) == 2
            assert markup.inline_keyboard[0][0].callback_data == "t_start:task_a"
            assert markup.inline_keyboard[1][0].callback_data == "t_start:task_b"

    asyncio.run(run())


def test_callback_t_start():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'reading'.") as mock_start:
            callback = MagicMock()
            callback.data = "t_start:reading"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_start_callback(callback)

            mock_start.assert_called_once_with("reading")
            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once_with("Started timer for 'reading'.")

    asyncio.run(run())


def test_callback_t_start_message_deleted_race():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'reading'."):
            callback = MagicMock()
            callback.data = "t_start:reading"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=Exception("TelegramBadRequest: message to edit not found"))
            callback.answer = AsyncMock()

            # Should not raise exception
            await timer_handler.process_timer_start_callback(callback)
            callback.answer.assert_called_once()

    asyncio.run(run())


def test_callback_t_stop_message_deleted_race():
    async def run():
        with patch("tracker.timer.TimerStop", return_value="Timer stopped successfully for 'coding'."):
            callback = MagicMock()
            callback.data = "t_stop:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=Exception("TelegramBadRequest: message to edit not found"))
            callback.answer = AsyncMock()

            # Should not raise exception
            await timer_handler.process_timer_stop_callback(callback)
            callback.answer.assert_called_once_with("⏹ Стоп")

    asyncio.run(run())


def test_callback_t_evening_top3():
    async def run():
        fake_candidates = [
            {"task_name": "t1", "role": "r1", "weekly_done": 10, "weekly_target": 60, "weekly_gap": 50},
            {"task_name": "t2", "role": "r2", "weekly_done": 20, "weekly_target": 60, "weekly_gap": 40},
            {"task_name": "t3", "role": "r3", "weekly_done": 30, "weekly_target": 60, "weekly_gap": 30},
        ]
        with patch("tracker.evening.get_evening_focus", return_value={"candidates": fake_candidates}):
            callback = MagicMock()
            callback.data = "t_evening_top3"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_evening_top3(callback)

            callback.answer.assert_called_once()
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]

            assert "🌙 <b>РЕЖИМ ВЕЧЕРНЕГО ДОБОРА (Evening Focus 2.0)</b>" in text
            assert "1️⃣ <b>t1</b>" in text
            assert "2️⃣ <b>t2</b>" in text
            assert "3️⃣ <b>t3</b>" in text
            # Row 1: sprint buttons for top 3
            assert len(markup.inline_keyboard[0]) == 3
            assert markup.inline_keyboard[0][0].callback_data == "eve_start:t1:20"

    asyncio.run(run())


def test_timer_status_running_markup():
    async def run():
        tasks = [{"task_name": "coding", "is_running": True}]
        with patch("tracker.timer.TimerList", return_value=tasks):
            with patch("tracker.timer.TimerStatus", return_value="Timer running: 'coding', Elapsed: 12m 34s"):
                message = MagicMock()
                message.text = "/timer_status"
                message.from_user.id = const.ADMIN_ID
                message.answer = AsyncMock()

                await timer_handler.command_timer_status(message)

                message.answer.assert_called_once()
                args, kwargs = message.answer.call_args
                text = args[0]
                markup = kwargs["reply_markup"]

                assert "Timer running: 'coding', Elapsed: 12m 34s" in text
                assert len(markup.inline_keyboard) == 1
                row = markup.inline_keyboard[0]
                assert row[0].text == "⏸ Пауза"
                assert row[0].callback_data == "t_pause:coding"
                assert row[1].text == "⏹ Стоп"
                assert row[1].callback_data == "t_stop:coding"
                assert row[2].text == "🔄 Сменить"
                assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_timer_status_paused_markup():
    async def run():
        tasks = [{"task_name": "writing", "is_running": False}]
        with patch("tracker.timer.TimerList", return_value=tasks):
            with patch("tracker.timer.TimerStatus", return_value="Timer paused: 'writing', Elapsed: 05m 00s"):
                message = MagicMock()
                message.text = "/timer_status"
                message.from_user.id = const.ADMIN_ID
                message.answer = AsyncMock()

                await timer_handler.command_timer_status(message)

                message.answer.assert_called_once()
                args, kwargs = message.answer.call_args
                text = args[0]
                markup = kwargs["reply_markup"]

                assert "Timer paused: 'writing', Elapsed: 05m 00s" in text
                assert len(markup.inline_keyboard) == 1
                row = markup.inline_keyboard[0]
                assert row[0].text == "▶️ Возобновить"
                assert row[0].callback_data == "t_resume:writing"
                assert row[1].text == "⏹ Стоп"
                assert row[1].callback_data == "t_stop:writing"
                assert row[2].text == "🔄 Сменить"
                assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_timer_status_empty():
    async def run():
        with patch("tracker.timer.TimerList", return_value=[]):
            with patch("tracker.timer.TimerStatus", return_value="No timers are currently active."):
                message = MagicMock()
                message.text = "/timer_status"
                message.from_user.id = const.ADMIN_ID
                message.answer = AsyncMock()

                await timer_handler.command_timer_status(message)

                message.answer.assert_called_once_with("No active timers found.")

    asyncio.run(run())


def test_completion_push_card_keyboard():
    markup = get_completion_push_card_keyboard(
        current_task="english",
        next_task="work",
        extend_minutes=15,
        rest_minutes=10,
    )
    assert len(markup.inline_keyboard) == 3
    # Row 1: Next task
    assert markup.inline_keyboard[0][0].text == "▶️ Запустить work"
    assert markup.inline_keyboard[0][0].callback_data == "t_start:work"
    # Row 2: Rest & Extend
    assert markup.inline_keyboard[1][0].text == "☕️ Перерыв 10м"
    assert markup.inline_keyboard[1][0].callback_data == "t_rest:10"
    assert markup.inline_keyboard[1][1].text == "⏳ Продлить +15м"
    assert markup.inline_keyboard[1][1].callback_data == "t_extend:english:15"
    # Row 3: Evening top 3
    assert markup.inline_keyboard[2][0].text == "🌙 Вечерний топ-3"
    assert markup.inline_keyboard[2][0].callback_data == "t_evening_top3"


def test_rest_spend_and_add_openapi_payload():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res_spend = rest.SpendRest(10)
        assert "Spent 10 minutes of rest." in res_spend
        mock_post.assert_called_once_with(
            const.REST_SPEND_URI,
            json={"rest_time": 10},
        )

    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res_add = rest.AddRest(15)
        assert "Added 15 minutes of rest." in res_add
        mock_post.assert_called_once_with(
            const.REST_ADD_URI,
            json={"rest_time": 15},
        )


def test_timer_start_with_target_duration():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res = timer.TimerStart("deep_work", target_duration=25)
        assert "Started timer for 'deep_work'." in res
        mock_post.assert_called_once_with(
            const.TIMER_RUN_START,
            json={"task_name": "deep_work", "target_duration": 25},
        )


def test_callback_t_extend_default_15_minutes():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'coding'.") as mock_start:
            callback = MagicMock()
            callback.data = "t_extend:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_extend_callback(callback)

            mock_start.assert_called_once_with("coding", target_duration=15)
            callback.answer.assert_called_once_with("+15 мин")

    asyncio.run(run())


def test_callback_t_extend_failure():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Failed to start timer: status code 500"):
            callback = MagicMock()
            callback.data = "t_extend:coding:10"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_extend_callback(callback)

            callback.message.edit_text.assert_called_once_with("Failed to start timer: status code 500")

    asyncio.run(run())


def test_callback_t_rest_failure():
    async def run():
        with patch("tracker.rest.SpendRest", return_value="Failed to spend rest with status code: 400"):
            callback = MagicMock()
            callback.data = "t_rest:10"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_rest_callback(callback)

            callback.message.edit_text.assert_called_once_with("Failed to spend rest with status code: 400")

    asyncio.run(run())


def test_callback_t_switch_empty():
    async def run():
        with patch("tracker.stats.GetTaskList", return_value=[]):
            callback = MagicMock()
            callback.data = "t_switch"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_switch_callback(callback)

            callback.message.edit_text.assert_called_once_with("No tasks available to switch.")

    asyncio.run(run())


def test_parse_timer_status_string():
    assert timer_handler.parse_timer_status_string("Timer running: 'work', Elapsed: 01m 00s") == ("work", True)
    assert timer_handler.parse_timer_status_string("Timer paused: 'learn', Elapsed: 02m 00s") == ("learn", False)
    assert timer_handler.parse_timer_status_string("No timers are currently active.") is None


def test_process_timer_start_message_fsm():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'fsm_task'.") as mock_start:
            message = MagicMock()
            message.text = "fsm_task"
            message.answer = AsyncMock()
            state = MagicMock()
            state.clear = AsyncMock()

            await timer_handler.process_timer_start_message(message, state)

            mock_start.assert_called_once_with("fsm_task")
            state.clear.assert_called_once()
            message.answer.assert_called_once_with("Started timer for 'fsm_task'.")

    asyncio.run(run())


def test_command_timer_start_direct_text_no_duplicate_keyboard():
    async def run():
        with patch("tracker.timer.TimerStart", return_value="Started timer for 'direct_task'.") as mock_start:
            message = MagicMock()
            message.text = "/timer_start direct_task"
            message.from_user.id = const.ADMIN_ID
            message.answer = AsyncMock()
            state = MagicMock()

            with patch("tracker.const.ADMIN_ID", const.ADMIN_ID):
                await timer_handler.command_timer_start(message, state)

            mock_start.assert_called_once_with("direct_task")
            message.answer.assert_called_once_with("Started timer for 'direct_task'.")

    asyncio.run(run())



LONG_TASK = "Изучение распределённых систем и консенсуса Raft"  # > 64 bytes in UTF-8


def test_task_callback_falls_back_to_hash_for_long_names():
    from keyboards.callback import task_callback, task_hash

    assert task_callback("t_stop", "coding") == "t_stop:coding"
    data = task_callback("t_extend", LONG_TASK, ":15")
    assert data == f"t_extend:#{task_hash(LONG_TASK)}:15"
    assert len(data.encode("utf-8")) <= 64
    for markup in (get_running_timer_keyboard(LONG_TASK), get_paused_timer_keyboard(LONG_TASK),
                   get_completion_push_card_keyboard(LONG_TASK, next_task=LONG_TASK)):
        for row in markup.inline_keyboard:
            for btn in row:
                assert len(btn.callback_data.encode("utf-8")) <= 64


def test_task_hash_matches_server_encoding():
    # Same value as tracker-server internal/notify/telegram TestCallbackDataHashesLongNames
    from keyboards.callback import task_hash
    assert task_hash(LONG_TASK) == "68efd5438f7d"


def test_callback_hashed_stop_resolves_task_name():
    from keyboards.callback import task_callback

    async def run():
        with patch("tracker.timer.TimerList", return_value=[{"task_name": LONG_TASK, "is_running": True}]), \
             patch("tracker.stats.GetTaskList", return_value=[]), \
             patch("tracker.timer.TimerStop", return_value="Timer stopped.") as mock_stop:
            callback = MagicMock()
            callback.data = task_callback("t_stop", LONG_TASK)
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_stop_callback(callback)
            mock_stop.assert_called_once_with(LONG_TASK)

    asyncio.run(run())


def test_callback_numeric_task_name_is_not_treated_as_index():
    async def run():
        with patch("tracker.timer.TimerList", return_value=[{"task_name": "other"}, {"task_name": "2026"}]), \
             patch("tracker.timer.TimerStop", return_value="Timer stopped.") as mock_stop:
            callback = MagicMock()
            callback.data = "t_stop:1"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_stop_callback(callback)
            mock_stop.assert_called_once_with("1")

    asyncio.run(run())


def test_callback_t_pause_failure_keeps_keyboard():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Failed to pause timer: status code 500"):
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            original = get_running_timer_keyboard("coding")
            callback.message.reply_markup = original
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert text.startswith("Failed")
            assert markup is original

    asyncio.run(run())


def test_callback_t_pause_unresolved_hash():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused.") as mock_pause, \
             patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.stats.GetTaskList", return_value=[]):
            callback = MagicMock()
            callback.data = "t_pause:#123456789abc"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)

            mock_pause.assert_called_once_with("")
            callback.answer.assert_called_once_with("⏸ Пауза")
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert "Timer paused." in text
            assert len(markup.inline_keyboard) == 1
            row = markup.inline_keyboard[0]
            assert row[0].text == "▶️ Возобновить"
            assert row[0].callback_data == "t_resume:"
            assert row[1].text == "⏹ Стоп"
            assert row[1].callback_data == "t_stop:"
            assert row[2].text == "🔄 Сменить"
            assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_callback_t_pause_edit_text_exception_fallback():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused.") as mock_pause:
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=Exception("TelegramBadRequest: message is not modified"))
            callback.message.edit_reply_markup = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)

            mock_pause.assert_called_once_with("coding")
            callback.answer.assert_called_once_with("⏸ Пауза")
            callback.message.edit_text.assert_called_once()
            callback.message.edit_reply_markup.assert_called_once()


def test_callback_t_pause_both_edits_fail_safe():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused."):
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=Exception("TelegramBadRequest: message to edit not found"))
            callback.message.edit_reply_markup = AsyncMock(side_effect=Exception("TelegramBadRequest: message to edit not found"))
            callback.answer = AsyncMock()

            # Should not raise exception
            await timer_handler.process_timer_pause_callback(callback)
            callback.answer.assert_called_once_with("⏸ Пауза")


def test_callback_t_pause_server_exception_safe():
    async def run():
        with patch("tracker.timer.TimerPause", side_effect=Exception("Connection refused")):
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.reply_markup = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            # Should not crash
            await timer_handler.process_timer_pause_callback(callback)
            callback.answer.assert_called_once_with("⏸ Пауза")
            callback.message.edit_text.assert_called_once()
            assert "Failed to pause timer" in callback.message.edit_text.call_args[0][0]


def test_callback_t_resume_unresolved_hash():
    async def run():
        with patch("tracker.timer.TimerResume", return_value="Timer resumed.") as mock_resume, \
             patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.stats.GetTaskList", return_value=[]):
            callback = MagicMock()
            callback.data = "t_resume:#123456789abc"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_resume_callback(callback)

            mock_resume.assert_called_once_with("")
            callback.answer.assert_called_once_with("▶️ Возобновить")
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert "Timer resumed." in text
            assert len(markup.inline_keyboard) == 1
            row = markup.inline_keyboard[0]
            assert row[0].text == "⏸ Пауза"
            assert row[0].callback_data == "t_pause:"
            assert row[1].text == "⏹ Стоп"
            assert row[1].callback_data == "t_stop:"
            assert row[2].text == "🔄 Сменить"
            assert row[2].callback_data == "t_switch"

    asyncio.run(run())


def test_callback_t_pause_telegram_bad_request_not_modified():
    from aiogram.exceptions import TelegramBadRequest

    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused."):
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(
                side_effect=TelegramBadRequest(method=None, message="Bad Request: message is not modified")
            )
            callback.message.edit_reply_markup = AsyncMock()
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)

            callback.answer.assert_called_once_with("⏸ Пауза")
            callback.message.edit_text.assert_called_once()
            callback.message.edit_reply_markup.assert_called_once()

    asyncio.run(run())


def test_callback_t_pause_unexpected_edit_error_logged():
    async def run():
        with patch("tracker.timer.TimerPause", return_value="Timer paused."), \
             patch("handlers.timer.logger.error") as mock_logger:
            callback = MagicMock()
            callback.data = "t_pause:coding"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock(side_effect=RuntimeError("Unexpected Telegram API error"))
            callback.answer = AsyncMock()

            await timer_handler.process_timer_pause_callback(callback)

            mock_logger.assert_called_once()
            assert "Unexpected error editing message" in mock_logger.call_args[0][0]

    asyncio.run(run())


def test_task_record_callback_resolves_hashed_name():
    from handlers import task_record as task_record_handler
    from keyboards.callback import task_callback

    async def run():
        with patch("tracker.timer.TimerList", return_value=[]), \
             patch("tracker.stats.GetTaskList", return_value=[{"name": LONG_TASK}]):
            callback = MagicMock()
            callback.data = task_callback("task", LONG_TASK)
            callback.message.edit_text = AsyncMock()
            state = MagicMock()
            state.update_data = AsyncMock()
            state.set_state = AsyncMock()

            await task_record_handler.task_handler(callback, state)
            state.update_data.assert_called_once_with(task=LONG_TASK)

    asyncio.run(run())


def test_task_record_typed_task_name_does_not_crash():
    from handlers import task_record as task_record_handler

    async def run():
        message = MagicMock()
        message.text = "  reading  "
        message.answer = AsyncMock()
        state = MagicMock()
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        await task_record_handler.task_message_handler(message, state)
        state.update_data.assert_called_once_with(task="reading")
        state.set_state.assert_called_once_with(task_record_handler.TaskRecord.time)
        message.answer.assert_called_once_with("Enter time in minutes")

    asyncio.run(run())


def test_task_record_invalid_time_reprompts():
    from handlers import task_record as task_record_handler

    async def run():
        with patch("tracker.task_record.AddTaskRecord") as mock_add:
            message = MagicMock()
            message.text = "abc"
            message.answer = AsyncMock()
            state = MagicMock()
            state.update_data = AsyncMock()
            state.clear = AsyncMock()

            await task_record_handler.time_handler(message, state)
            mock_add.assert_not_called()
            state.clear.assert_not_called()
            assert "positive whole number" in message.answer.call_args[0][0]

    asyncio.run(run())
