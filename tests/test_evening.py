import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from handlers import evening as evening_handler


def test_format_evening_focus_message():
    candidates = [
        {
            "task_name": "reading",
            "role": "hobby",
            "weekly_done": 30,
            "weekly_target": 120,
            "weekly_gap": 90,
        },
        {
            "task_name": "sport",
            "role": "health",
            "weekly_done": 60,
            "weekly_target": 180,
            "weekly_gap": 120,
        },
    ]
    msg = evening_handler.format_evening_focus_message(candidates)
    assert "🌙 <b>РЕЖИМ ВЕЧЕРНЕГО ДОБОРА (Evening Focus 2.0)</b>\n\n" in msg
    assert "1️⃣ <b>reading</b> [hobby]\n   📊 Неделя: 30/120 мин (дефицит: 90 мин)\n" in msg
    assert "2️⃣ <b>sport</b> [health]\n   📊 Неделя: 60/180 мин (дефицит: 120 мин)\n" in msg


def test_build_evening_keyboard_3_candidates():
    candidates = [
        {"task_name": "task_one"},
        {"task_name": "task_two"},
        {"task_name": "task_three_longname"},
    ]
    markup = evening_handler.build_evening_keyboard(candidates, sprint_time=20)
    assert len(markup.inline_keyboard) == 3

    # Row 1: individual launch buttons with name[:10]
    row1 = markup.inline_keyboard[0]
    assert len(row1) == 3
    assert row1[0].text == "▶️ 1️⃣ task_one"
    assert row1[0].callback_data == "eve_start:task_one:20"
    assert row1[1].text == "▶️ 2️⃣ task_two"
    assert row1[1].callback_data == "eve_start:task_two:20"
    assert row1[2].text == "▶️ 3️⃣ task_three"
    assert row1[2].callback_data == "eve_start:task_three_longname:20"

    # Row 2: combo and skip
    row2 = markup.inline_keyboard[1]
    assert len(row2) == 2
    assert row2[0].text == "⚡️ Комбо 3x10м"
    assert row2[0].callback_data == "eve_combo:10"
    assert row2[1].text == "⏭️ Пропустить #1"
    assert row2[1].callback_data == "eve_skip:task_one:20"

    # Row 3: time presets
    row3 = markup.inline_keyboard[2]
    assert len(row3) == 3
    assert row3[0].text == "⏱️ 15m"
    assert row3[0].callback_data == "eve_time:15"
    assert row3[1].text == "⏱️ 20m"
    assert row3[1].callback_data == "eve_time:20"
    assert row3[2].text == "⏱️ 30m"
    assert row3[2].callback_data == "eve_time:30"


def test_build_evening_keyboard_2_candidates():
    candidates = [
        {"task_name": "task_one"},
        {"task_name": "task_two"},
    ]
    markup = evening_handler.build_evening_keyboard(candidates, sprint_time=15)
    row1 = markup.inline_keyboard[0]
    assert len(row1) == 2
    assert row1[0].text == "▶️ 1️⃣ task_one"
    assert row1[1].text == "▶️ 2️⃣ task_two"

    row2 = markup.inline_keyboard[1]
    assert row2[0].text == "⚡️ Комбо 2x10м"
    assert row2[1].text == "⏭️ Пропустить #1"


def test_command_evening_empty():
    async def run():
        with patch("tracker.evening.get_evening_focus", return_value={"candidates": []}):
            message = MagicMock()
            message.from_user.id = 111111111
            message.answer = AsyncMock()
            with patch("tracker.const.ADMIN_ID", 111111111):
                await evening_handler.command_evening_handler(message)
            message.answer.assert_called_once_with("🎉 Отличная работа! Все задачи на эту неделю выполнены.")

    asyncio.run(run())


def test_command_evening_with_candidates():
    async def run():
        fake_candidates = [
            {"task_name": "t1", "role": "r1", "weekly_done": 10, "weekly_target": 60, "weekly_gap": 50},
            {"task_name": "t2", "role": "r2", "weekly_done": 20, "weekly_target": 60, "weekly_gap": 40},
            {"task_name": "t3", "role": "r3", "weekly_done": 30, "weekly_target": 60, "weekly_gap": 30},
            {"task_name": "t4", "role": "r4", "weekly_done": 40, "weekly_target": 60, "weekly_gap": 20},
        ]
        with patch("tracker.evening.get_evening_focus", return_value={"candidates": fake_candidates}):
            message = MagicMock()
            message.from_user.id = 111111111
            message.answer = AsyncMock()
            with patch("tracker.const.ADMIN_ID", 111111111):
                await evening_handler.command_evening_handler(message)
            message.answer.assert_called_once()
            args, kwargs = message.answer.call_args
            text = args[0]
            markup = kwargs["reply_markup"]
            assert "1️⃣ <b>t1</b> [r1]" in text
            assert "2️⃣ <b>t2</b> [r2]" in text
            assert "3️⃣ <b>t3</b> [r3]" in text
            assert "4️⃣" not in text  # capped at top 3
            assert len(markup.inline_keyboard[0]) == 3

    asyncio.run(run())


def test_process_evening_skip():
    async def run():
        fake_candidates = [
            {"task_name": "next_task", "role": "work", "weekly_done": 0, "weekly_target": 60, "weekly_gap": 60}
        ]
        with patch("tracker.evening.skip_evening_task", return_value={"candidates": fake_candidates}) as mock_skip:
            callback = MagicMock()
            callback.data = "eve_skip:old_task:20"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_skip(callback)
            mock_skip.assert_called_once_with("old_task", sprint_time=20)
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            assert "1️⃣ <b>next_task</b>" in text
            callback.answer.assert_called_once()

    asyncio.run(run())


def test_process_evening_time():
    async def run():
        fake_candidates = [
            {"task_name": "task_a", "role": "learn", "weekly_done": 10, "weekly_target": 60, "weekly_gap": 50}
        ]
        with patch("tracker.evening.get_evening_focus", return_value={"candidates": fake_candidates}) as mock_focus:
            callback = MagicMock()
            callback.data = "eve_time:30"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_time(callback)
            mock_focus.assert_called_once_with(sprint_time=30)
            callback.message.edit_text.assert_called_once()
            markup = callback.message.edit_text.call_args[1]["reply_markup"]
            assert markup.inline_keyboard[0][0].callback_data == "eve_start:task_a:30"
            callback.answer.assert_called_once()

    asyncio.run(run())


def test_process_evening_combo_3_steps():
    async def run():
        fake_candidates = [
            {"task_name": "task_1", "role": "learn", "weekly_done": 10, "weekly_target": 60, "weekly_gap": 50},
            {"task_name": "task_2", "role": "dev", "weekly_done": 20, "weekly_target": 60, "weekly_gap": 40},
            {"task_name": "task_3", "role": "read", "weekly_done": 30, "weekly_target": 60, "weekly_gap": 30},
        ]
        evening_handler.COMBO_SESSIONS.clear()
        user_id = 99999

        with patch("tracker.evening.get_evening_focus", return_value={"candidates": fake_candidates}), \
             patch("tracker.timer.start_task", return_value={"status": "success"}) as mock_start:
            
            # Step 1: Initial launch
            callback = MagicMock()
            callback.from_user.id = user_id
            callback.data = "eve_combo:10"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_combo(callback)

            mock_start.assert_called_with(task_name="task_1", target_duration=10)
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            text = args[0]
            markup = kwargs["reply_markup"]

            assert text == "⚡️ Запущено комбо 3x10м! Шаг 1/3: task_1 (10 мин).\nПосле завершения запустите Шаг 2/3: task_2."
            assert len(markup.inline_keyboard) == 1
            advance_button = markup.inline_keyboard[0][0]
            assert advance_button.text == "▶️ Шаг 2: task_2 (10m)"
            assert advance_button.callback_data == "eve_combo:next"

            # Step 2: Advance to task_2
            callback.data = "eve_combo:next"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_combo(callback)

            mock_start.assert_called_with(task_name="task_2", target_duration=10)
            callback.message.edit_text.assert_called_once()
            args, kwargs = callback.message.edit_text.call_args
            text = args[0]
            markup = kwargs["reply_markup"]

            assert text == "⚡️ Комбо 3x10м! Шаг 2/3: task_2 (10 мин).\nПосле завершения запустите Шаг 3/3: task_3."
            assert len(markup.inline_keyboard) == 1
            advance_button = markup.inline_keyboard[0][0]
            assert advance_button.text == "▶️ Шаг 3: task_3 (10m)"
            assert advance_button.callback_data == "eve_combo:next"

            # Step 3: Final step task_3
            callback.data = "eve_combo:next"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_combo(callback)

            mock_start.assert_called_with(task_name="task_3", target_duration=10)
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]

            assert text == "⚡️ Комбо 3x10м! Шаг 3/3: task_3 (10 мин). Финальный спринт комбо-цепочки! 🎉"
            assert user_id not in evening_handler.COMBO_SESSIONS

    asyncio.run(run())


def test_process_evening_combo_single_candidate():
    async def run():
        fake_candidates = [
            {"task_name": "only_task", "role": "learn", "weekly_done": 10, "weekly_target": 60, "weekly_gap": 50},
        ]
        evening_handler.COMBO_SESSIONS.clear()
        user_id = 99999

        with patch("tracker.evening.get_evening_focus", return_value={"candidates": fake_candidates}), \
             patch("tracker.timer.start_task", return_value={"status": "success"}) as mock_start:
            
            callback = MagicMock()
            callback.from_user.id = user_id
            callback.data = "eve_combo:10"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_combo(callback)

            mock_start.assert_called_once_with(task_name="only_task", target_duration=10)
            text = callback.message.edit_text.call_args[0][0]
            assert text == "⚡️ Запущен спринт комбо! Шаг 1/1: only_task (10 мин)."
            assert user_id not in evening_handler.COMBO_SESSIONS

    asyncio.run(run())


def test_process_evening_combo_expired_session():
    async def run():
        evening_handler.COMBO_SESSIONS.clear()
        callback = MagicMock()
        callback.from_user.id = 99999
        callback.data = "eve_combo:next"
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        await evening_handler.process_evening_combo(callback)
        callback.message.edit_text.assert_called_once_with("⚠️ Сессия комбо истекла. Запустите /evening заново.")
        callback.answer.assert_called_once()

    asyncio.run(run())


def test_process_evening_start():
    async def run():
        with patch("tracker.timer.start_task", return_value={"status": "success"}) as mock_start:
            callback = MagicMock()
            callback.data = "eve_start:task_1:20"
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await evening_handler.process_evening_start(callback)

            mock_start.assert_called_once_with(task_name="task_1", target_duration=20)
            callback.message.edit_text.assert_called_once_with("🚀 Запущен вечерний спринт по 'task_1' на 20 минут!")
            callback.answer.assert_called_once()

    asyncio.run(run())
