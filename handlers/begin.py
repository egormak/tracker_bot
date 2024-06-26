from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
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

@router.message(CommandStart())
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Open WebApp", web_app=InlineKeyboardButton.WebAppInfo(url="https://<username>.github.io/<repository-name>"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Click the button below to open the WebApp:', reply_markup=reply_markup)
