from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold

from tracker import general, evening, timer

router = Router()


def build_evening_keyboard(current_task_name: str, sprint_time: int = 20):
    buttons = []
    if current_task_name:
        buttons.append([
            InlineKeyboardButton(text=f"▶️ Старт {sprint_time}m", callback_data=f"eve_start:{current_task_name}:{sprint_time}"),
            InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"eve_skip:{current_task_name}:{sprint_time}")
        ])

    buttons.append([
        InlineKeyboardButton(text="⏱️ 15m", callback_data=f"eve_time:15"),
        InlineKeyboardButton(text="⏱️ 20m", callback_data=f"eve_time:20"),
        InlineKeyboardButton(text="⏱️ 30m", callback_data=f"eve_time:30"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("evening"))
@general.telegram_auth
async def command_evening_handler(message: Message) -> None:
    data = evening.get_evening_focus(sprint_time=20)
    current_task = data.get("current_task", {})
    task_name = current_task.get("task_name", "")
    gap = current_task.get("weekly_gap", 0)

    if not task_name:
        await message.answer("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        return

    text = (
        f"🌙 {hbold('РЕЖИМ ВЕЧЕРНЕГО ДОБОРА (Evening Focus)')}\n\n"
        f"🎯 {hbold('Рекомендуемая задача:')} {task_name}\n"
        f"📉 {hbold('Недельное отставание:')} -{gap} мин\n"
        f"⏱️ {hbold('Целевой спринт:')} 20 мин (Лимит отдыха: 10 мин)"
    )

    markup = build_evening_keyboard(task_name, sprint_time=20)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("eve_skip:"))
async def process_evening_skip(callback: CallbackQuery):
    parts = callback.data.split(":")
    task_name = parts[1]
    sprint_time = int(parts[2]) if len(parts) > 2 else 20

    data = evening.skip_evening_task(task_name, sprint_time=sprint_time)
    current_task = data.get("current_task", {})
    next_task_name = current_task.get("task_name", "")
    gap = current_task.get("weekly_gap", 0)

    if not next_task_name:
        await callback.message.edit_text("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        await callback.answer()
        return

    text = (
        f"🌙 {hbold('РЕЖИМ ВЕЧЕРНЕГО ДОБОРА (Evening Focus)')}\n\n"
        f"ℹ️ Задача '{task_name}' пропущена на сегодня\n"
        f"🎯 {hbold('Рекомендуемая задача:')} {next_task_name}\n"
        f"📉 {hbold('Недельное отставание:')} -{gap} мин\n"
        f"⏱️ {hbold('Целевой спринт:')} {sprint_time} мин (Лимит отдыха: 10 мин)"
    )

    markup = build_evening_keyboard(next_task_name, sprint_time=sprint_time)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("eve_start:"))
async def process_evening_start(callback: CallbackQuery):
    parts = callback.data.split(":")
    task_name = parts[1]
    sprint_time = int(parts[2]) if len(parts) > 2 else 20

    res = timer.start_task(task_name=task_name, target_duration=sprint_time)
    if res.get("status") == "success":
        await callback.message.edit_text(f"🚀 Запущен вечерний спринт по '{task_name}' на {sprint_time} минут!")
    else:
        await callback.message.edit_text(f"❌ Ошибка при запуске: {res.get('message', 'Unknown error')}")
    await callback.answer()
