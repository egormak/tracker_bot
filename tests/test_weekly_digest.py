import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from handlers import statistic as statistic_handler
from keyboards.timer import get_completion_push_card_keyboard
from tracker import stats, errors

DIGEST = {
    "week": "current",
    "week_start_date": "5 October 2026",
    "week_end_date": "11 October 2026",
    "total_planned": 310,
    "total_done": 320,
    "roles": [
        {"role": "work", "planned": 200, "done": 200, "share_percent": 62},
        {"role": "rest", "planned": 70, "done": 120, "share_percent": 37},
    ],
    "strict": [{"name": "work", "role": "work", "planned": 200, "done": 200, "plan_percent": 100, "share_percent": 100}],
    "free": [
        {"name": "video", "role": "rest", "planned": 10, "done": 90, "plan_percent": 900, "share_percent": 75},
        {"name": "games", "role": "rest", "planned": 60, "done": 0, "plan_percent": 0, "share_percent": 0},
    ],
    "free_done": 120,
    "over_plan": [{"name": "video", "role": "rest", "planned": 10, "done": 90, "delta": 80}],
    "untouched": [{"name": "games", "role": "rest", "planned": 60, "done": 0, "delta": -60}],
    "unscheduled": [{"name": "telegram", "role": "rest", "planned": 0, "done": 30, "delta": 30}],
    "days": [{"day": "monday", "date": "5 October 2026", "total_done": 150}],
    "busiest_day": {"day": "monday", "date": "5 October 2026", "total_done": 150},
}


def test_format_weekly_digest():
    text = stats.FormatWeeklyDigest(DIGEST)
    for line in [
        "📊 Итоги недели: 5 October 2026 — 11 October 2026",
        "Всего: 5ч 20м из 5ч 10м по плану (103%)",
        "• work: 3ч 20м из 3ч 20м · 62% времени",
        "• work: 3ч 20м из 3ч 20м (100%)",
        "Свободное время (2ч):",
        "• video: 1ч 30м · 75% · план 10м",
        "• сверх плана — video: +1ч 20м",
        "• не начато — games: план 1ч",
        "• без расписания — telegram: 30м",
        "Самый нагруженный день: monday — 2ч 30м",
    ]:
        assert line in text.split("\n"), f"missing line: {line}\n{text}"
    # Free tasks with no time are listed once, under "не начато", not in the ranking.
    assert "• games: 0м" not in text


def test_format_weekly_digest_empty_week():
    text = stats.FormatWeeklyDigest({"week_start_date": "12 October 2026", "week_end_date": "18 October 2026", "total_done": 0})
    assert text == "📊 Итоги недели: 12 October 2026 — 18 October 2026\nЗа эту неделю записей нет."


def test_get_weekly_digest_requests_week():
    response = MagicMock(status_code=200)
    response.json.return_value = DIGEST
    with patch("tracker.stats.requests.get", return_value=response) as mock_get:
        text = stats.GetWeeklyDigest("previous")
    assert mock_get.call_args[1]["params"] == {"week": "previous"}
    assert text.startswith("📊 Итоги недели")


def test_get_weekly_digest_error_status():
    with patch("tracker.stats.requests.get", return_value=MagicMock(status_code=500)):
        try:
            stats.GetWeeklyDigest()
        except errors.InvalidStatusCode:
            return
    assert False, "expected InvalidStatusCode"


def _message(text):
    message = MagicMock()
    message.text = text
    message.from_user.id = 1
    message.answer = AsyncMock()
    return message


def test_week_command_selects_week():
    async def run():
        with patch("tracker.const.ADMIN_ID", 1), \
             patch("tracker.stats.GetWeeklyDigest", return_value="digest") as mock_digest:
            for text, week in [("/week", "current"), ("/week prev", "previous"), ("/week previous", "previous")]:
                message = _message(text)
                await statistic_handler.command_week(message)
                assert mock_digest.call_args[0][0] == week
                message.answer.assert_called_once_with("digest")

    asyncio.run(run())


def test_week_digest_callback_keeps_the_card():
    async def run():
        with patch("tracker.stats.GetWeeklyDigest", return_value="digest") as mock_digest:
            callback = MagicMock()
            callback.data = "week_digest"
            callback.answer = AsyncMock()
            callback.message = MagicMock()
            callback.message.answer = AsyncMock()
            callback.message.edit_text = AsyncMock()

            await statistic_handler.process_week_digest(callback)

            mock_digest.assert_called_once_with("current")
            callback.message.answer.assert_called_once_with("digest")
            callback.message.edit_text.assert_not_called()

    asyncio.run(run())


def test_week_digest_callback_reports_error():
    async def run():
        with patch("tracker.stats.GetWeeklyDigest", side_effect=errors.InvalidStatusCode("boom")):
            callback = MagicMock()
            callback.answer = AsyncMock()
            callback.message = MagicMock()
            callback.message.answer = AsyncMock()
            await statistic_handler.process_week_digest(callback)
            assert "boom" in callback.message.answer.call_args[0][0]

    asyncio.run(run())


def test_completion_card_weekly_digest_row():
    card = get_completion_push_card_keyboard("work", weekly_digest=True)
    assert card.inline_keyboard[-1][0].callback_data == "week_digest"
    assert "week_digest" not in [b.callback_data for row in get_completion_push_card_keyboard("work").inline_keyboard for b in row]
