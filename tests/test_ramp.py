import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import requests

from handlers import ramp as ramp_handler
from keyboards.ramp import get_ramp_keyboard
from tracker import ramp as ramp_tracker, const
from tracker.ramp import RampStatus, RampConfig


def test_format_ramp_message_dict():
    status = {
        "current_step": 3,
        "today_focus_minutes": 6,
        "cap_minutes": 25,
        "config": {
            "enabled_roles": ["work", "learn"],
        },
    }
    msg = ramp_handler.format_ramp_message(status)
    expected = (
        "⚡️ Лестница линейного разгона (Warm-Up Ramp)\n"
        "• Текущая ступень: 3 мин\n"
        "• Фокус сегодня: 6 мин\n"
        "• Потолок: 25 мин\n"
        "• Активные роли: work, learn"
    )
    assert msg == expected


def test_format_ramp_message_model():
    status = RampStatus(
        current_step=4,
        cap_minutes=20,
        today_focus_minutes=10,
        config=RampConfig(
            cap_minutes=20,
            enabled_roles=["work", "learn", "reading"],
        ),
    )
    msg = ramp_handler.format_ramp_message(status)
    expected = (
        "⚡️ Лестница линейного разгона (Warm-Up Ramp)\n"
        "• Текущая ступень: 4 мин\n"
        "• Фокус сегодня: 10 мин\n"
        "• Потолок: 20 мин\n"
        "• Активные роли: work, learn, reading"
    )
    assert msg == expected


def test_format_ramp_message_defaults():
    msg = ramp_handler.format_ramp_message({})
    assert "• Текущая ступень: 1 мин" in msg
    assert "• Фокус сегодня: 0 мин" in msg
    assert "• Потолок: 25 мин" in msg
    assert "• Активные роли: " in msg


def test_format_ramp_message_flat_enabled_roles():
    status = {
        "current_step": 2,
        "today_focus_minutes": 1,
        "cap_minutes": 25,
        "enabled_roles": ["work"],
    }
    msg = ramp_handler.format_ramp_message(status)
    assert "• Текущая ступень: 2 мин" in msg
    assert "• Активные роли: work" in msg


def test_get_ramp_keyboard():
    markup = get_ramp_keyboard()
    assert len(markup.inline_keyboard) == 1
    row = markup.inline_keyboard[0]
    assert len(row) == 1
    button = row[0]
    assert button.text == "🔄 Сбросить на 1м"
    assert button.callback_data == "ramp:reset"


def test_command_ramp_authorized():
    async def run():
        fake_status = {
            "current_step": 5,
            "today_focus_minutes": 15,
            "cap_minutes": 25,
            "config": {"enabled_roles": ["work", "learn"]},
        }
        with patch("tracker.ramp.get_ramp_status", return_value=fake_status) as mock_get:
            message = MagicMock()
            message.from_user.id = 123456
            message.answer = AsyncMock()

            with patch("tracker.const.ADMIN_ID", 123456):
                await ramp_handler.command_ramp_handler(message)

            mock_get.assert_called_once()
            message.answer.assert_called_once()
            args, kwargs = message.answer.call_args
            text = args[0]
            markup = kwargs["reply_markup"]

            assert "• Текущая ступень: 5 мин" in text
            assert "• Фокус сегодня: 15 мин" in text
            assert "• Потолок: 25 мин" in text
            assert "• Активные роли: work, learn" in text
            assert markup.inline_keyboard[0][0].callback_data == "ramp:reset"

    asyncio.run(run())


def test_command_ramp_unauthorized():
    async def run():
        message = MagicMock()
        message.from_user.id = 999999
        message.reply = AsyncMock()

        with patch("tracker.const.ADMIN_ID", 123456):
            await ramp_handler.command_ramp_handler(message)

        message.reply.assert_called_once()
        assert "Access Denied" in message.reply.call_args[0][0]

    asyncio.run(run())


def test_process_ramp_reset():
    async def run():
        fake_reset_status = {
            "current_step": 1,
            "today_focus_minutes": 15,
            "cap_minutes": 25,
            "config": {"enabled_roles": ["work", "learn"]},
        }
        with patch("tracker.ramp.reset_ramp", return_value=fake_reset_status) as mock_reset:
            callback = MagicMock()
            callback.data = "ramp:reset"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await ramp_handler.process_ramp_reset(callback)

            mock_reset.assert_called_once()
            callback.answer.assert_called_once_with("✅ Разгон сброшен на 1 мин")
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            assert "• Текущая ступень: 1 мин" in text
            assert "• Фокус сегодня: 15 мин" in text
            assert "• Активные роли: work, learn" in text

    asyncio.run(run())


def test_process_ramp_reset_fallback_on_empty():
    async def run():
        with patch("tracker.ramp.reset_ramp", return_value={}) as mock_reset:
            callback = MagicMock()
            callback.data = "ramp:reset"
            callback.message = MagicMock()
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()

            await ramp_handler.process_ramp_reset(callback)

            mock_reset.assert_called_once()
            callback.answer.assert_called_once_with("✅ Разгон сброшен на 1 мин")
            callback.message.edit_text.assert_called_once()
            text = callback.message.edit_text.call_args[0][0]
            assert "• Текущая ступень: 1 мин" in text

    asyncio.run(run())


def test_tracker_ramp_get_status_success():
    fake_data = {
        "current_step": 3,
        "cap_minutes": 25,
        "is_capped": False,
        "today_focus_minutes": 6,
        "date": "23 September 2026",
        "config": {
            "cap_minutes": 25,
            "enabled_roles": ["work", "learn"],
            "enabled_tasks": ["home_task"],
            "excluded_tasks": ["video"],
            "default_rest_fallback": 15,
        },
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: fake_data)
        result = ramp_tracker.get_ramp_status()
        assert result == fake_data
        mock_get.assert_called_once_with(const.RAMP_STATUS_URI)


def test_tracker_ramp_get_status_wrapped_data():
    fake_inner = {"current_step": 2, "cap_minutes": 25, "today_focus_minutes": 1}
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": fake_inner},
        )
        result = ramp_tracker.get_ramp_status()
        assert result == fake_inner


def test_tracker_ramp_get_status_error():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=500)
        result = ramp_tracker.get_ramp_status()
        assert result == {}

    with patch("requests.get", side_effect=requests.RequestException("Network down")):
        result = ramp_tracker.get_ramp_status()
        assert result == {}


def test_tracker_ramp_reset_success():
    fake_data = {
        "current_step": 1,
        "cap_minutes": 25,
        "is_capped": False,
        "today_focus_minutes": 6,
        "date": "23 September 2026",
        "config": {
            "cap_minutes": 25,
            "enabled_roles": ["work", "learn"],
            "enabled_tasks": ["home_task"],
            "excluded_tasks": ["video"],
            "default_rest_fallback": 15,
        },
    }
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: fake_data)
        result = ramp_tracker.reset_ramp()
        assert result == fake_data
        mock_post.assert_called_once_with(const.RAMP_RESET_URI)


def test_tracker_ramp_reset_error():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=500)
        result = ramp_tracker.reset_ramp()
        assert result == {}

    with patch("requests.post", side_effect=requests.RequestException("Connection error")):
        result = ramp_tracker.reset_ramp()
        assert result == {}


def test_get_ramp_status_model():
    fake_data = {
        "current_step": 3,
        "cap_minutes": 25,
        "is_capped": False,
        "today_focus_minutes": 6,
        "date": "23 September 2026",
        "config": {
            "cap_minutes": 25,
            "enabled_roles": ["work", "learn"],
            "enabled_tasks": ["home_task"],
            "excluded_tasks": ["video"],
            "default_rest_fallback": 15,
        },
    }
    with patch("tracker.ramp.get_ramp_status", return_value=fake_data):
        model = ramp_tracker.get_ramp_status_model()
        assert isinstance(model, RampStatus)
        assert model.current_step == 3
        assert model.config.enabled_roles == ["work", "learn"]
