from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, WebAppInfo
from aiogram.utils.markdown import hbold

from tracker import general
from keyboards.quick import get_main_keyboard

router = Router()

# The "/" menu in Telegram; set from main.py at startup.
BOT_COMMANDS = [
    BotCommand(command="go", description="Запустить задачу"),
    BotCommand(command="now", description="Что идёт сейчас"),
    BotCommand(command="today", description="Статистика за сегодня"),
    BotCommand(command="debt", description="Долг прошлых дней"),
    BotCommand(command="week", description="Итоги недели (prev — прошлая)"),
    BotCommand(command="break", description="Перерыв по настроению"),
    BotCommand(command="evening", description="Вечерний добор: топ-3"),
    BotCommand(command="ramp", description="Разгон (Warm-Up)"),
    BotCommand(command="menu", description="Показать кнопки"),
    BotCommand(command="help", description="Все команды"),
]

HELP_TEXT = (
    f"{hbold('Кнопки внизу:')}\n"
    "▶️ Задачи — выбрать задачу и время, закрыть долг\n"
    "⏯ Сейчас — пауза / стоп / сменить\n"
    "📊 Сегодня — план и факт за день\n"
    "💳 Долг — долг прошлых дней по задачам\n\n"
    f"{hbold('Текстом:')}\n"
    "video — запустить на остаток дня (или 30 мин)\n"
    "video 45 — на 45 минут\n"
    "video долг — закрыть долг video\n"
    "video 60 50% — 60 минут, половина в долг\n\n"
    f"{hbold('Команды:')}\n"
    "/go /now /today /debt — то же, что кнопки\n"
    "/week [prev] — итоги недели\n"
    "/break — перерыв по настроению\n"
    "/evening — вечерний добор (топ-3)\n"
    "/ramp — разгон (Warm-Up)\n"
    "/nexttask — следующая задача по расписанию\n"
    "/taskrecordadd — добавить запись вручную\n"
    "/webapp — открыть Mini App\n"
    "/timer_start /timer_pause /timer_resume /timer_stop /timer_status — таймер командами\n"
    "/menu — вернуть кнопки"
)


@router.message(CommandStart())
@general.telegram_auth
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! Кнопки внизу, /help — все команды.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )

@router.message(Command("webapp"))
async def webapp(message: Message) -> None:
    keyboard = [
        [InlineKeyboardButton(text="Open WebApp", web_app=WebAppInfo(url="https://tracker.makegorka.com/"))]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer('Click the button below to open the WebApp:', reply_markup=reply_markup)

@router.message(Command("help"))
async def command_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=get_main_keyboard(), parse_mode="HTML")
