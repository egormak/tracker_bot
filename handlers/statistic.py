from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tracker import general
from tracker import stats
from handlers import quick

router = Router()

@router.message(Command("stats"))
@general.telegram_auth
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/stats` command: the same card as the "📊 Сегодня" button
    """
    await quick.send_today(message)

@router.message(Command("tasklist"))
@general.telegram_auth
async def command_task_list(message: Message) -> None:
    """
    This handler receives messages with `/tasklist` command
    """
    try:
        task_list = stats.GetTaskList()
    except Exception as e:
        await message.answer(str(e))
        return
    answer_msg = ""
    for task in task_list or []:
        answer_msg += f"{task['name']}\n - time_duration: {task['time_duration']} - time_done: {task['time_done']} - time_left: {task['time_duration'] - task['time_done']}\n\n"
    # Telegram rejects an empty message.
    await message.answer(answer_msg or "На сегодня задач нет.")

@router.message(Command("nexttask"))
@general.telegram_auth
async def command_next_task(message: Message) -> None:
    """
    This handler receives messages with `/nexttask` command
    """
    try:
        answer_msg = stats.GetNextTask()
        await message.answer(answer_msg)
    except Exception as e:
        await message.answer(str(e))


def _weekly_digest_text(week: str) -> str:
    try:
        return stats.GetWeeklyDigest(week)
    except Exception as e:
        return str(e)


@router.message(Command("week"))
@general.telegram_auth
async def command_week(message: Message) -> None:
    """
    This handler receives messages with `/week` command; `/week prev` shows the previous week
    """
    args = (message.text or "").split(maxsplit=1)
    previous = len(args) > 1 and args[1].strip().lower().startswith("prev")
    await message.answer(_weekly_digest_text("previous" if previous else "current"))


@router.callback_query(F.data == "week_digest")
async def process_week_digest(callback: CallbackQuery) -> None:
    # Sent as a new message: the completion card it sits on keeps its other buttons.
    await callback.answer()
    await callback.message.answer(_weekly_digest_text("current"))
