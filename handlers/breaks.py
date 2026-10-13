import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tracker import general, evening, timer
from handlers.task_callback import try_resolve_task_token, answer_unknown_task, split_task_payload
from keyboards.breaks import (
    DEFAULT_BREAK_MINUTES,
    get_break_selector_keyboard,
    with_break_duration,
)

logger = logging.getLogger(__name__)

router = Router()


def _break_option_names() -> list[str]:
    return [o.get("task_name", "") for o in evening.get_break_options().get("options", [])]


async def render_break_selector(message: Message, edit: bool = False) -> None:
    options = evening.get_break_options().get("options", [])
    if not options:
        text, markup = "Нет задач для перерыва.", None
    else:
        text = "☕️ Перерыв: что запустить?\n🎲 — меньше всего на этой неделе."
        markup = get_break_selector_keyboard(options)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("break"))
@general.telegram_auth
async def command_break_handler(message: Message) -> None:
    await render_break_selector(message)


@router.callback_query(F.data == "brk_menu")
async def process_break_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await render_break_selector(callback.message, edit=True)
    except Exception:
        await render_break_selector(callback.message)


@router.callback_query(F.data.startswith("t_brkdur:"))
async def process_break_duration(callback: CallbackQuery) -> None:
    value = callback.data.split(":", 1)[1]
    minutes = int(value) if value.isdigit() else DEFAULT_BREAK_MINUTES
    await callback.answer(f"{minutes} мин")
    markup = callback.message.reply_markup
    if markup is None:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=with_break_duration(markup, minutes))
    except Exception as e:
        # Tapping the duration that is already selected changes nothing.
        if "message is not modified" not in str(e).lower():
            logger.warning("Failed to update break duration keyboard: %s", e)


@router.callback_query(F.data.startswith("t_brk:"))
async def process_break_start(callback: CallbackQuery) -> None:
    token, min_str = split_task_payload(callback.data, "t_brk:")
    minutes = int(min_str) if min_str.isdigit() else DEFAULT_BREAK_MINUTES
    task_name = try_resolve_task_token(token, extra_names=_break_option_names)
    if task_name is None:
        await answer_unknown_task(callback, "Откройте /break заново")
        return

    res = timer.TimerStart(task_name, target_duration=minutes)
    await callback.answer()
    try:
        if res.startswith("Failed"):
            await callback.message.edit_text(res)
        else:
            await callback.message.edit_text(f"☕️ '{task_name}' запущена на {minutes} мин.")
    except Exception:
        pass
