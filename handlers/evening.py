from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold

from tracker import general, evening, timer

router = Router()

# In-memory session store: user_id -> {"candidates": [task_names...], "combo_time": int, "step": int}
COMBO_SESSIONS: dict[int, dict] = {}


def format_evening_focus_message(candidates: list) -> str:
    text = "🌙 <b>РЕЖИМ ВЕЧЕРНЕГО ДОБОРА (Evening Focus 2.0)</b>\n\n"
    for i, candidate in enumerate(candidates, 1):
        task_name = candidate.get("task_name", "")
        role = candidate.get("role", "")
        weekly_done = candidate.get("weekly_done", 0)
        weekly_target = candidate.get("weekly_target", 0)
        weekly_gap = candidate.get("weekly_gap", 0)
        text += (
            f"{i}️⃣ <b>{task_name}</b> [{role}]\n"
            f"   📊 Неделя: {weekly_done}/{weekly_target} мин (дефицит: {weekly_gap} мин)\n"
        )
    return text


def build_evening_keyboard(candidates, sprint_time: int = 20) -> InlineKeyboardMarkup:
    if isinstance(candidates, str):
        candidates = [{"task_name": candidates}] if candidates else []
    buttons = []
    if candidates:
        row1 = [
            InlineKeyboardButton(
                text=f"▶️ {i}️⃣ {c.get('task_name', '')[:10]}",
                callback_data=f"eve_start:{c.get('task_name', '')}:{sprint_time}"
            )
            for i, c in enumerate(candidates, 1)
        ]
        buttons.append(row1)

        num_cand = len(candidates)
        combo_label = f"⚡️ Комбо {num_cand}x10м" if num_cand > 1 else "⚡️ Комбо 1x10м"
        top_task_name = candidates[0].get("task_name", "")
        row2 = [
            InlineKeyboardButton(text=combo_label, callback_data="eve_combo:10"),
            InlineKeyboardButton(text="⏭️ Пропустить #1", callback_data=f"eve_skip:{top_task_name}:{sprint_time}")
        ]
        buttons.append(row2)

    row3 = [
        InlineKeyboardButton(text="⏱️ 15m", callback_data="eve_time:15"),
        InlineKeyboardButton(text="⏱️ 20m", callback_data="eve_time:20"),
        InlineKeyboardButton(text="⏱️ 30m", callback_data="eve_time:30"),
    ]
    buttons.append(row3)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("evening"))
@general.telegram_auth
async def command_evening_handler(message: Message) -> None:
    sprint_time = 20
    data = evening.get_evening_focus(sprint_time=sprint_time)
    candidates = data.get("candidates", [])[:3]

    if not candidates:
        await message.answer("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        return

    text = format_evening_focus_message(candidates)
    markup = build_evening_keyboard(candidates, sprint_time=sprint_time)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("eve_skip:"))
async def process_evening_skip(callback: CallbackQuery):
    parts = callback.data.split(":")
    task_name = parts[1]
    sprint_time = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20

    data = evening.skip_evening_task(task_name, sprint_time=sprint_time)
    candidates = data.get("candidates", [])[:3]

    if not candidates:
        await callback.message.edit_text("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        await callback.answer()
        return

    text = format_evening_focus_message(candidates)
    markup = build_evening_keyboard(candidates, sprint_time=sprint_time)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("eve_time:"))
async def process_evening_time(callback: CallbackQuery):
    parts = callback.data.split(":")
    sprint_time = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20

    data = evening.get_evening_focus(sprint_time=sprint_time)
    candidates = data.get("candidates", [])[:3]

    if not candidates:
        await callback.message.edit_text("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        await callback.answer()
        return

    text = format_evening_focus_message(candidates)
    markup = build_evening_keyboard(candidates, sprint_time=sprint_time)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("eve_combo:"))
async def process_evening_combo(callback: CallbackQuery):
    user_id = callback.from_user.id if callback.from_user else (callback.message.chat.id if callback.message and callback.message.chat else 0)

    if callback.data == "eve_combo:next":
        session = COMBO_SESSIONS.get(user_id)
        if not session:
            await callback.message.edit_text("⚠️ Сессия комбо истекла. Запустите /evening заново.")
            await callback.answer()
            return

        session["step"] += 1
        cur_step = session["step"]
        candidates = session["candidates"]
        total_steps = len(candidates)
        combo_time = session["combo_time"]

        task_name = candidates[cur_step - 1]
        res = timer.start_task(task_name=task_name, target_duration=combo_time)
        if isinstance(res, dict) and res.get("status") == "error":
            await callback.message.edit_text(f"❌ Ошибка при запуске: {res.get('message', 'Unknown error')}")
            await callback.answer()
            return

        if cur_step < total_steps:
            next_task = candidates[cur_step]
            text = (
                f"⚡️ Комбо {total_steps}x{combo_time}м! Шаг {cur_step}/{total_steps}: {task_name} ({combo_time} мин).\n"
                f"После завершения запустите Шаг {cur_step + 1}/{total_steps}: {next_task}."
            )
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"▶️ Шаг {cur_step + 1}: {next_task[:10]} ({combo_time}m)",
                    callback_data="eve_combo:next"
                )
            ]])
            await callback.message.edit_text(text, reply_markup=markup)
        else:
            text = f"⚡️ Комбо {total_steps}x{combo_time}м! Шаг {total_steps}/{total_steps}: {task_name} ({combo_time} мин). Финальный спринт комбо-цепочки! 🎉"
            COMBO_SESSIONS.pop(user_id, None)
            await callback.message.edit_text(text)
        await callback.answer()
        return

    # Base combo trigger: eve_combo:{combo_time}
    parts = callback.data.split(":")
    combo_time = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10

    data = evening.get_evening_focus(sprint_time=combo_time)
    top = data.get("candidates", [])[:3]

    if not top:
        await callback.message.edit_text("🎉 Отличная работа! Все задачи на эту неделю выполнены.")
        await callback.answer()
        return

    total_steps = len(top)
    task_1 = top[0].get("task_name", "")
    res = timer.start_task(task_name=task_1, target_duration=combo_time)
    if isinstance(res, dict) and res.get("status") == "error":
        await callback.message.edit_text(f"❌ Ошибка при запуске: {res.get('message', 'Unknown error')}")
        await callback.answer()
        return

    if total_steps > 1:
        COMBO_SESSIONS[user_id] = {
            "candidates": [c.get("task_name", "") for c in top],
            "combo_time": combo_time,
            "step": 1,
        }
        task_2 = top[1].get("task_name", "")
        text = (
            f"⚡️ Запущено комбо {total_steps}x{combo_time}м! Шаг 1/{total_steps}: {task_1} ({combo_time} мин).\n"
            f"После завершения запустите Шаг 2/{total_steps}: {task_2}."
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"▶️ Шаг 2: {task_2[:10]} ({combo_time}m)",
                callback_data="eve_combo:next"
            )
        ]])
        await callback.message.edit_text(text, reply_markup=markup)
    else:
        text = f"⚡️ Запущен спринт комбо! Шаг 1/1: {task_1} ({combo_time} мин)."
        await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data.startswith("eve_start:"))
async def process_evening_start(callback: CallbackQuery):
    parts = callback.data.split(":")
    task_name = parts[1]
    sprint_time = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20

    res = timer.start_task(task_name=task_name, target_duration=sprint_time)
    if isinstance(res, dict) and res.get("status") == "error":
        await callback.message.edit_text(f"❌ Ошибка при запуске: {res.get('message', 'Unknown error')}")
    else:
        await callback.message.edit_text(f"🚀 Запущен вечерний спринт по '{task_name}' на {sprint_time} минут!")
    await callback.answer()
