from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from tracker import general, rest

router = Router()

class RestAddState(StatesGroup):
    time = State()

class RestSpendState(StatesGroup):
    time = State()

@router.message(Command("restadd"))
@general.telegram_auth_with_state
async def command_rest_add(message: Message, state: FSMContext) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        try:
            mins = int(parts[1])
            res = rest.AddRest(mins)
            await message.answer(res)
        except ValueError:
            await message.answer("Please provide a valid integer for minutes.")
    else:
        await message.answer("How many minutes of rest do you want to add?")
        await state.set_state(RestAddState.time)

@router.message(RestAddState.time)
async def process_rest_add(message: Message, state: FSMContext) -> None:
    try:
        mins = int(message.text)
        res = rest.AddRest(mins)
        await message.answer(res)
    except ValueError:
        await message.answer("Please provide a valid integer. Canceling.")
    finally:
        await state.clear()


@router.message(Command("restspend"))
@general.telegram_auth_with_state
async def command_rest_spend(message: Message, state: FSMContext) -> None:
    parts = message.text.split()
    if len(parts) > 1:
        try:
            mins = int(parts[1])
            res = rest.SpendRest(mins)
            await message.answer(res)
        except ValueError:
            await message.answer("Please provide a valid integer for minutes.")
    else:
        await message.answer("How many minutes of rest do you want to spend?")
        await state.set_state(RestSpendState.time)

@router.message(RestSpendState.time)
async def process_rest_spend(message: Message, state: FSMContext) -> None:
    try:
        mins = int(message.text)
        res = rest.SpendRest(mins)
        await message.answer(res)
    except ValueError:
        await message.answer("Please provide a valid integer. Canceling.")
    finally:
        await state.clear()

@router.message(Command("restget"))
@general.telegram_auth
async def command_rest_get(message: Message) -> None:
    try:
        res = rest.GetRest()
        await message.answer(res)
    except Exception as e:
        await message.answer(f"Error querying rest: {str(e)}")
