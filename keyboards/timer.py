from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .callback import task_callback


def get_running_timer_keyboard(task_name: str) -> InlineKeyboardMarkup:
    """Returns remote keyboard for running timer: [⏸ Пауза], [⏹ Стоп], [🔄 Сменить]."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸ Пауза", callback_data=task_callback("t_pause", task_name)),
                InlineKeyboardButton(text="⏹ Стоп", callback_data=task_callback("t_stop", task_name)),
                InlineKeyboardButton(text="🔄 Сменить", callback_data="t_switch"),
            ]
        ]
    )


def get_paused_timer_keyboard(task_name: str) -> InlineKeyboardMarkup:
    """Returns remote keyboard for paused timer: [▶️ Возобновить], [⏹ Стоп], [🔄 Сменить]."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Возобновить", callback_data=task_callback("t_resume", task_name)),
                InlineKeyboardButton(text="⏹ Стоп", callback_data=task_callback("t_stop", task_name)),
                InlineKeyboardButton(text="🔄 Сменить", callback_data="t_switch"),
            ]
        ]
    )


def get_completion_push_card_keyboard(
    current_task: str,
    next_task: str = "",
    extend_minutes: int = 15,
    rest_minutes: int = 10,
) -> InlineKeyboardMarkup:
    """Returns inline keyboard for session completion push card."""
    buttons = []
    if next_task:
        buttons.append([
            InlineKeyboardButton(text=f"▶️ Запустить {next_task}", callback_data=task_callback("t_start", next_task))
        ])
    buttons.append([
        InlineKeyboardButton(text=f"☕️ Перерыв {rest_minutes}м", callback_data=f"t_rest:{rest_minutes}"),
        InlineKeyboardButton(text=f"⏳ Продлить +{extend_minutes}м", callback_data=task_callback("t_extend", current_task, f":{extend_minutes}")),
    ])
    buttons.append([
        InlineKeyboardButton(text="🌙 Вечерний топ-3", callback_data="t_evening_top3")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
