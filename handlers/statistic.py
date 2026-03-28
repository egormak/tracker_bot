from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tracker import general
from tracker import stats

router = Router()

@router.message(Command("stats"))
@general.telegram_auth
async def command_start_handler(message: Message) -> None:

    """
    This handler receives messages with `/stats` command
    """
    answer_msg = stats.GetStats()
    await message.answer(answer_msg)

@router.message(Command("tasklist"))
@general.telegram_auth
async def command_task_list(message: Message) -> None:
    """
    This handler receives messages with `/tasklist` command
    """
    task_list = stats.GetTaskList()
    answer_msg = ""
    for task in task_list:
        answer_msg += f"{task['name']}\n - time_duration: {task['time_duration']} - time_done: {task['time_done']} - time_left: {task['time_duration'] - task['time_done']}\n\n"
    await message.answer(answer_msg)

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
