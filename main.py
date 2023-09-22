import asyncio
import logging
import sys
import yaml

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from tracker import const, stats
import config

# All handlers should be attached to the Router (or Dispatcher)
router = Router()

def telegram_auth(func):
    async def wrapper(message):
        if message.from_user.id != const.ADMIN_ID:
            return await message.reply(f"Access Denied: {hbold(message.from_user.id)}")
        return await func(message)
    return wrapper

@router.message(CommandStart())
@telegram_auth
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")

@router.message(Command("stats"))
@telegram_auth
async def command_start_handler(message: Message) -> None:

    """
    This handler receives messages with `/stats` command
    """
    answer_msg = stats.GetStats()
    await message.answer(answer_msg)

@router.message()
@telegram_auth
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Dispatcher is a root router
    dp = Dispatcher()
    # ... and all other routers should be attached to Dispatcher
    dp.include_router(router)

    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(config.config["telegram"]["token"], parse_mode=ParseMode.HTML)
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
