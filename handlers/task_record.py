from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from tracker import general, task_record, errors, stats

router = Router()

class TaskRecord(StatesGroup):
    task = State()
    time = State()

@router.message(Command("taskrecordadd"))
@general.telegram_auth_with_state
async def command_start_handler(message: Message, state: FSMContext) -> None:

    """
    This handler receives messages with `/taskrecordadd` command
    """
    # answer_msg = stats.GetStats()
    if len(message.text.split()) > 1:
        result = task_record.AddTaskRecord(message.text)
        await message.answer(result)
    else:
        keyboard = []
        try:
            list_task = stats.GetTaskList()
            for task in list_task:
                button = [InlineKeyboardButton(text=f"{task['name']} - {task['time_duration'] - task['time_done']}", callback_data=f"task:{task['name']}")]
                keyboard.append(button)
            menu = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await message.answer("Choose task:", reply_markup=menu)
            await state.set_state(TaskRecord.task)
        except errors.InvalidStatusCode as e:
            await message.answer(e.message)
            return

@router.callback_query(lambda c: c.data.startswith("task:"))
@router.message(TaskRecord.task)
# @general.telegram_auth
async def task_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(task=callback.data.split(":")[1])
    await state.set_state(TaskRecord.time)
    await callback.message.edit_text("Enter time in minutes")

@router.message(TaskRecord.time)
# @general.telegram_auth
async def time_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(time=message.text)
    data = await state.get_data()
    # result = task_record.AddTaskRecord(f"task={data.get('task')}&time={data.get('time')}")
    result = task_record.AddTaskRecord(task_name=data.get('task'), time_done=int(data.get('time')))
    await message.answer("result: " + result + ", task: " + data.get('task') + " time: " + data.get('time'))
    await state.clear()

@router.message(Command("task_plan_percent"))
@general.telegram_auth
async def command_task_plan_percent(message: Message) -> None:
    answer_msg = task_record.GetTaskPlanPercent()
    await message.answer(answer_msg)