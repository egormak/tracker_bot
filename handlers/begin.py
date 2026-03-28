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

@router.message(Command("help"))
async def command_help(message: Message) -> None:
    help_text = (
        f"{hbold('Available commands:')}\n"
        "/start - Start Bot\n"
        "/help - Show this help message\n"
        "/webapp - Open Mini WebApp\n"
        "/stats - Show task statistics\n"
        "/tasklist - Show task list\n"
        "/nexttask - Get the next task to work on based on schedule\n"
        "/taskrecordadd - Add a complete task record\n"
        "/task_plan_percent - Get current plan percentage\n\n"
        f"{hbold('Rest Management:')}\n"
        "/restadd [minutes] - Add rest minutes\n"
        "/restspend [minutes] - Spend rest minutes\n"
        "/restget - Get available rest time\n\n"
        f"{hbold('Timer Management:')}\n"
        "/timer_start [task_name] - Start a timer for a task\n"
        "/timer_stop - Stop the running timer\n"
        "/timer_pause - Pause the running timer\n"
        "/timer_resume - Resume the paused timer\n"
        "/timer_status - View active timer status"
    )
    await message.answer(help_text)
