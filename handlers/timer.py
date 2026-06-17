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

@router.message(Command("timer_stop"))
@general.telegram_auth
async def command_timer_stop(message: Message) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        res = timer.TimerStop(task_name)
        await message.answer(res)
        return

    tasks = timer.TimerList()
    if not tasks:
        await message.answer("No active timers found.")
        return
    if len(tasks) == 1:
        res = timer.TimerStop(tasks[0]["task_name"])
        await message.answer(res)
        return

    keyboard = []
    for t in tasks:
        name = t["task_name"]
        keyboard.append([InlineKeyboardButton(text=f"Stop {name}", callback_data=f"t_stop:{name}")])
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Choose task to stop:", reply_markup=menu)

@router.callback_query(lambda c: c.data.startswith("t_stop:"))
async def process_timer_stop_callback(callback: CallbackQuery) -> None:
    task_name = callback.data.split(":", 1)[1]
    res = timer.TimerStop(task_name)
    await callback.message.edit_text(res)

@router.message(Command("timer_pause"))
@general.telegram_auth
async def command_timer_pause(message: Message) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        res = timer.TimerPause(task_name)
        await message.answer(res)
        return

    tasks = timer.TimerList()
    if not tasks:
        await message.answer("No active timers found.")
        return
    running_tasks = [t for t in tasks if t.get("is_running", False)]
    if not running_tasks:
        await message.answer("No running timers found to pause.")
        return
    if len(running_tasks) == 1:
        res = timer.TimerPause(running_tasks[0]["task_name"])
        await message.answer(res)
        return

    keyboard = []
    for t in running_tasks:
        name = t["task_name"]
        keyboard.append([InlineKeyboardButton(text=f"Pause {name}", callback_data=f"t_pause:{name}")])
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Choose task to pause:", reply_markup=menu)

@router.callback_query(lambda c: c.data.startswith("t_pause:"))
async def process_timer_pause_callback(callback: CallbackQuery) -> None:
    task_name = callback.data.split(":", 1)[1]
    res = timer.TimerPause(task_name)
    await callback.message.edit_text(res)

@router.message(Command("timer_resume"))
@general.telegram_auth
async def command_timer_resume(message: Message) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        res = timer.TimerResume(task_name)
        await message.answer(res)
        return

    tasks = timer.TimerList()
    if not tasks:
        await message.answer("No active timers found.")
        return
    paused_tasks = [t for t in tasks if not t.get("is_running", False)]
    if not paused_tasks:
        await message.answer("No paused timers found to resume.")
        return
    if len(paused_tasks) == 1:
        res = timer.TimerResume(paused_tasks[0]["task_name"])
        await message.answer(res)
        return

    keyboard = []
    for t in paused_tasks:
        name = t["task_name"]
        keyboard.append([InlineKeyboardButton(text=f"Resume {name}", callback_data=f"t_resume:{name}")])
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Choose task to resume:", reply_markup=menu)

@router.callback_query(lambda c: c.data.startswith("t_resume:"))
async def process_timer_resume_callback(callback: CallbackQuery) -> None:
    task_name = callback.data.split(":", 1)[1]
    res = timer.TimerResume(task_name)
    await callback.message.edit_text(res)

@router.message(Command("timer_status"))
@general.telegram_auth
async def command_timer_status(message: Message) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        task_name = " ".join(parts[1:])
        try:
            res = timer.TimerStatus(task_name)
            await message.answer(res)
        except Exception as e:
            await message.answer(str(e))
        return

    tasks = timer.TimerList()
    if not tasks:
        await message.answer("No active timers found.")
        return
    if len(tasks) == 1:
        try:
            res = timer.TimerStatus(tasks[0]["task_name"])
            await message.answer(res)
        except Exception as e:
            await message.answer(str(e))
        return

    keyboard = []
    for t in tasks:
        name = t["task_name"]
        keyboard.append([InlineKeyboardButton(text=f"Status: {name}", callback_data=f"t_status:{name}")])
    menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Choose task to view status:", reply_markup=menu)

@router.callback_query(lambda c: c.data.startswith("t_status:"))
async def process_timer_status_callback(callback: CallbackQuery) -> None:
    task_name = callback.data.split(":", 1)[1]
    try:
        res = timer.TimerStatus(task_name)
        await callback.message.edit_text(res)
    except Exception as e:
        await callback.message.edit_text(str(e))
