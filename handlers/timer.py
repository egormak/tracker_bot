from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from tracker import general, timer, stats, rest, errors
from keyboards.callback import task_callback
from handlers.task_callback import resolve_task_token
from keyboards.timer import (
    get_running_timer_keyboard,
    get_paused_timer_keyboard,
)
from handlers import evening as evening_handler

router = Router()


class TimerStartState(StatesGroup):
    task = State()


def parse_timer_status_string(status_text: str) -> tuple[str, bool] | None:
    if "Timer running: '" in status_text:
        task_name = status_text.split("Timer running: '", 1)[1].split("'", 1)[0]
        return task_name, True
    elif "Timer paused: '" in status_text:
        task_name = status_text.split("Timer paused: '", 1)[1].split("'", 1)[0]
        return task_name, False
    return None


def _resolve_callback_task(callback_data: str, prefix: str) -> str:
    return resolve_task_token(callback_data[len(prefix):])


@router.message(Command("timer_start"))
@general.telegram_auth_with_state
async def command_timer_start(message: Message, state: FSMContext) -> None:
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        res = timer.TimerStart(task_name)
        await message.answer(res)
    else:
        keyboard = []
        try:
            list_task = stats.GetTaskList()
            for task in list_task:
                name = task.get("name") or task.get("task_name", "")
                dur = task.get("time_duration", 0)
                done = task.get("time_done", 0)
                button = [InlineKeyboardButton(text=f"{name} - left: {dur - done}", callback_data=task_callback("t_start", name))]
                keyboard.append(button)
            menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await message.answer("Choose task to start:", reply_markup=menu)
            await state.set_state(TimerStartState.task)
        except errors.InvalidStatusCode as e:
            await message.answer(e.message)
            return


@router.message(TimerStartState.task)
async def process_timer_start_message(message: Message, state: FSMContext) -> None:
    task_name = message.text.strip()
    res = timer.TimerStart(task_name)
    await state.clear()
    await message.answer(res)

def _safe_call(action_fn, task_name: str) -> str:
    try:
        return action_fn(task_name)
    except errors.InvalidStatusCode as e:
        return e.message


async def _handle_timer_command(
    message: Message,
    action_fn,
    filter_fn,
    prefix: str,
    button_label: str,
    prompt_word: str,
    empty_msg: str,
    filtered_empty_msg: str = None,
) -> None:
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        res = _safe_call(action_fn, task_name)
        await message.answer(res)
        return

    try:
        tasks = timer.TimerList()
    except errors.InvalidStatusCode as e:
        await message.answer(e.message)
        return

    if not tasks:
        await message.answer(empty_msg)
        return

    if filter_fn:
        tasks = filter_fn(tasks)
        if not tasks:
            await message.answer(filtered_empty_msg)
            return

    if len(tasks) == 1:
        res = _safe_call(action_fn, tasks[0]["task_name"])
        await message.answer(res)
        return

    keyboard = [
        [InlineKeyboardButton(text=f"{button_label} {t['task_name']}", callback_data=task_callback(prefix, t['task_name']))]
        for t in tasks
    ]
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(f"Choose task to {prompt_word}:", reply_markup=menu)


@router.message(Command("timer_stop"))
@general.telegram_auth
async def command_timer_stop(message: Message) -> None:
    await _handle_timer_command(
        message, timer.TimerStop, None, "t_stop", "Stop", "stop",
        "No active timers found.",
    )


@router.message(Command("timer_pause"))
@general.telegram_auth
async def command_timer_pause(message: Message) -> None:
    await _handle_timer_command(
        message, timer.TimerPause, timer.FilterRunning, "t_pause", "Pause", "pause",
        "No active timers found.", "No running timers found to pause.",
    )


@router.message(Command("timer_resume"))
@general.telegram_auth
async def command_timer_resume(message: Message) -> None:
    await _handle_timer_command(
        message, timer.TimerResume, timer.FilterPaused, "t_resume", "Resume", "resume",
        "No active timers found.", "No paused timers found to resume.",
    )


@router.message(Command("timer_status"))
@general.telegram_auth
async def command_timer_status(message: Message) -> None:
    parts = message.text.split() if message.text else []
    task_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Check TimerList first to determine active task and state
    try:
        tasks = timer.TimerList()
    except Exception:
        tasks = []

    if tasks:
        selected_task = None
        if task_name:
            for t in tasks:
                if t.get("task_name") == task_name:
                    selected_task = t
                    break
        if not selected_task:
            running_tasks = timer.FilterRunning(tasks)
            selected_task = running_tasks[0] if running_tasks else tasks[0]

        t_name = selected_task.get("task_name", "")
        is_running = selected_task.get("is_running", False)
        try:
            status_text = timer.TimerStatus(t_name)
        except Exception:
            status_text = f"Timer {'running' if is_running else 'paused'}: '{t_name}'"

        markup = get_running_timer_keyboard(t_name) if is_running else get_paused_timer_keyboard(t_name)
        await message.answer(status_text, reply_markup=markup)
        return

    # Fallback to TimerStatus
    try:
        status_text = timer.TimerStatus(task_name)
    except errors.InvalidStatusCode as e:
        await message.answer(e.message)
        return
    except Exception as e:
        await message.answer(f"Error checking timer status: {e}")
        return

    if not status_text or status_text == "No timers are currently active.":
        await message.answer("No active timers found.")
        return

    parsed = parse_timer_status_string(status_text)
    if parsed:
        t_name, is_running = parsed
        markup = get_running_timer_keyboard(t_name) if is_running else get_paused_timer_keyboard(t_name)
        await message.answer(status_text, reply_markup=markup)
        return

    await message.answer(status_text)


# --- Callback query handlers ---


@router.callback_query(F.data.startswith("t_pause:"))
async def process_timer_pause_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    task_name = _resolve_callback_task(callback.data, "t_pause:")
    res = timer.TimerPause(task_name)
    if res.startswith("Failed"):
        # Leave the existing keyboard alone: the server state did not change.
        try:
            await callback.message.edit_text(res, reply_markup=callback.message.reply_markup)
        except Exception:
            pass
        return
    markup = get_paused_timer_keyboard(task_name)
    try:
        await callback.message.edit_text(res, reply_markup=markup)
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=markup)


@router.callback_query(F.data.startswith("t_resume:"))
async def process_timer_resume_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    task_name = _resolve_callback_task(callback.data, "t_resume:")
    res = timer.TimerResume(task_name)
    if res.startswith("Failed"):
        # Leave the existing keyboard alone: the server state did not change.
        try:
            await callback.message.edit_text(res, reply_markup=callback.message.reply_markup)
        except Exception:
            pass
        return
    markup = get_running_timer_keyboard(task_name)
    try:
        await callback.message.edit_text(res, reply_markup=markup)
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=markup)


@router.callback_query(F.data.startswith("t_stop:"))
async def process_timer_stop_callback(callback: CallbackQuery) -> None:
    await callback.answer("⏹ Стоп")
    task_name = _resolve_callback_task(callback.data, "t_stop:")
    res = timer.TimerStop(task_name)
    try:
        await callback.message.edit_text(res)
    except Exception:
        pass


@router.callback_query(F.data.startswith("t_extend:"))
async def process_timer_extend_callback(callback: CallbackQuery) -> None:
    raw = callback.data[len("t_extend:"):]
    if ":" in raw:
        task_name, min_str = raw.rsplit(":", 1)
        task_name = resolve_task_token(task_name)
        minutes = int(min_str) if min_str.isdigit() else 15
    else:
        task_name = resolve_task_token(raw)
        minutes = 15

    res = timer.TimerStart(task_name, target_duration=minutes)
    await callback.answer(f"+{minutes} мин")
    try:
        if res.startswith("Failed"):
            await callback.message.edit_text(res)
        else:
            await callback.message.edit_text(f"⏳ Задача '{task_name}' продлена на +{minutes} мин.")
    except Exception:
        pass


@router.callback_query(F.data.startswith("t_rest:"))
async def process_timer_rest_callback(callback: CallbackQuery) -> None:
    min_str = callback.data.split(":", 1)[1]
    minutes = int(min_str) if min_str.isdigit() else 10
    res = rest.SpendRest(minutes)
    await callback.answer()
    if res.startswith("Failed"):
        await callback.message.edit_text(res)
    else:
        msg = f"☕️ Списано {minutes} мин отдыха. Приятного перерыва!"
        await callback.message.edit_text(msg)


@router.callback_query(F.data == "t_switch")
async def process_timer_switch_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        task_list = stats.GetTaskList()
    except errors.InvalidStatusCode as e:
        await callback.message.edit_text(e.message)
        return
    except Exception as e:
        await callback.message.edit_text(f"Error fetching tasks: {e}")
        return

    if not task_list:
        await callback.message.edit_text("No tasks available to switch.")
        return

    keyboard = []
    for task in task_list:
        name = task.get("name") or task.get("task_name")
        if not name:
            continue
        if "time_duration" in task and "time_done" in task:
            left = task["time_duration"] - task["time_done"]
            btn_text = f"{name} - left: {left}"
        else:
            btn_text = name
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=task_callback("t_start", name))])

    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text("Choose task to switch:", reply_markup=menu)


@router.callback_query(F.data.startswith("t_start:"))
async def process_timer_start_callback(callback: CallbackQuery, state: FSMContext = None) -> None:
    await callback.answer()
    task_name = _resolve_callback_task(callback.data, "t_start:")
    res = timer.TimerStart(task_name)
    if state:
        await state.clear()
    try:
        await callback.message.edit_text(res)
    except Exception:
        pass


@router.callback_query(F.data == "t_evening_top3")
async def process_timer_evening_top3(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await evening_handler.render_evening_triage(callback.message, sprint_time=20, edit=True)
    except Exception:
        await evening_handler.render_evening_triage(callback.message, sprint_time=20, edit=False)


@router.callback_query(F.data.startswith("t_status:"))
async def process_timer_status_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    task_name = _resolve_callback_task(callback.data, "t_status:")
    try:
        status_text = timer.TimerStatus(task_name)
    except errors.InvalidStatusCode as e:
        await callback.message.edit_text(e.message)
        return

    parsed = parse_timer_status_string(status_text)
    if parsed:
        t_name, is_running = parsed
        markup = get_running_timer_keyboard(t_name) if is_running else get_paused_timer_keyboard(t_name)
        await callback.message.edit_text(status_text, reply_markup=markup)
    else:
        await callback.message.edit_text(status_text)
