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
