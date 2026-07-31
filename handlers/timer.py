from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from tracker import general, timer, stats, errors

router = Router()

class TimerStartState(StatesGroup):
    task = State()

@router.message(Command("timer_start"))
@general.telegram_auth_with_state
async def command_timer_start(message: Message, state: FSMContext) -> None:
    parts = message.text.split()
    if len(parts) > 1:
         # Simplified: passing task name as rest of text
        task_name = " ".join(parts[1:])
        res = timer.TimerStart(task_name)
        await message.answer(res)
    else:
        keyboard = []
        try:
            list_task = stats.GetTaskList()
            for task in list_task:
                # Need unique callback payload prefix
                button = [InlineKeyboardButton(text=f"{task['name']} - left: {task['time_duration'] - task['time_done']}", callback_data=f"t_start:{task['name']}")]
                keyboard.append(button)
            menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await message.answer("Choose task to start:", reply_markup=menu)
            await state.set_state(TimerStartState.task)
        except errors.InvalidStatusCode as e:
            await message.answer(e.message)
            return

@router.callback_query(lambda c: c.data.startswith("t_start:"))
@router.message(TimerStartState.task)
async def process_timer_start(callback: CallbackQuery, state: FSMContext) -> None:
    task_name = callback.data.split(":")[1]
    res = timer.TimerStart(task_name)
    await callback.message.edit_text(res)
    await state.clear()

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
    parts = message.text.split()
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
        [InlineKeyboardButton(text=f"{button_label} {t['task_name']}", callback_data=f"{prefix}:{i}")]
        for i, t in enumerate(tasks)
    ]
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(f"Choose task to {prompt_word}:", reply_markup=menu)


# Maps a button-prefix to the tracker action it performs and the task filter
# (if any) used both to build that keyboard and to resolve its callback index.
_TIMER_ACTIONS = {
    "t_stop": (timer.TimerStop, None),
    "t_pause": (timer.TimerPause, timer.FilterRunning),
    "t_resume": (timer.TimerResume, timer.FilterPaused),
    "t_status": (timer.TimerStatus, None),
}


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
    await _handle_timer_command(
        message, timer.TimerStatus, None, "t_status", "Status:", "view status",
        "No active timers found.",
    )


@router.callback_query(lambda c: (c.data or "").split(":", 1)[0] in _TIMER_ACTIONS)
async def process_timer_action_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    prefix, idx_str = callback.data.split(":", 1)
    action_fn, filter_fn = _TIMER_ACTIONS[prefix]

    try:
        tasks = timer.TimerList()
    except errors.InvalidStatusCode as e:
        await callback.message.edit_text(e.message)
        return

    if filter_fn:
        tasks = filter_fn(tasks)

    idx = int(idx_str)
    if idx >= len(tasks):
        await callback.message.edit_text("Task no longer available.")
        return

    task_name = tasks[idx]["task_name"]
    res = _safe_call(action_fn, task_name)
    await callback.message.edit_text(res)
