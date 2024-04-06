from . import const
from aiogram.utils.markdown import hbold

def telegram_auth_with_state(func):
    async def wrapper(message, state):
        if message.from_user.id != const.ADMIN_ID:
            return await message.reply(f"Access Denied: {hbold(message.from_user.id)}")
        return await func(message, state)
    return wrapper

def telegram_auth(func):
    async def wrapper(message):
        if message.from_user.id != const.ADMIN_ID:
            return await message.reply(f"Access Denied: {hbold(message.from_user.id)}")
        return await func(message)
    return wrapper
