from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_ramp_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard with reset button for warm-up ramp."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сбросить на 1м", callback_data="ramp:reset")]
        ]
    )
