from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.utils.markdown import hbold

from tracker import general

router = Router()

@router.message(CommandStart())
@general.telegram_auth
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")

@router.message(Command("webapp"))
async def webapp(message: Message) -> None:
    keyboard = [
        [InlineKeyboardButton(text="Open WebApp", web_app=WebAppInfo(url="https://egormak.github.io/tracker-web-mini/"))]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer('Click the button below to open the WebApp:', reply_markup=reply_markup)
