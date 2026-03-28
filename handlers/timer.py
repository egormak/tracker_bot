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
    res = timer.TimerStop()
    await message.answer(res)

@router.message(Command("timer_pause"))
@general.telegram_auth
async def command_timer_pause(message: Message) -> None:
    res = timer.TimerPause()
    await message.answer(res)

@router.message(Command("timer_resume"))
@general.telegram_auth
async def command_timer_resume(message: Message) -> None:
    res = timer.TimerResume()
    await message.answer(res)

@router.message(Command("timer_status"))
@general.telegram_auth
async def command_timer_status(message: Message) -> None:
    try:
        res = timer.TimerStatus()
        await message.answer(res)
    except Exception as e:
         await message.answer(str(e))
