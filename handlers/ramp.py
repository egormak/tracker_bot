from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from keyboards.ramp import get_ramp_keyboard
from tracker import general, ramp
from tracker.ramp import RampStatus

router = Router()

build_ramp_keyboard = get_ramp_keyboard


def format_ramp_message(status: dict | RampStatus) -> str:
    """Format warm-up ramp status message."""
    if isinstance(status, RampStatus):
        current_step = status.current_step
        today_focus_minutes = status.today_focus_minutes
        cap_minutes = status.cap_minutes
        roles = status.config.enabled_roles
    elif isinstance(status, dict):
        current_step = status.get("current_step", 1)
        today_focus_minutes = status.get("today_focus_minutes", 0)
        cap_minutes = status.get("cap_minutes", 25)
        cfg = status.get("config", {})
        if isinstance(cfg, dict):
            roles = cfg.get("enabled_roles", [])
        else:
            roles = getattr(cfg, "enabled_roles", [])
        if not roles and "enabled_roles" in status:
            roles = status.get("enabled_roles", [])
    else:
        current_step = 1
        today_focus_minutes = 0
        cap_minutes = 25
        roles = []

    if isinstance(roles, list):
        enabled_roles = ", ".join(str(r) for r in roles) if roles else ""
    elif isinstance(roles, str):
        enabled_roles = roles
    else:
        enabled_roles = ""

    return (
        "⚡️ Лестница линейного разгона (Warm-Up Ramp)\n"
        f"• Текущая ступень: {current_step} мин\n"
        f"• Фокус сегодня: {today_focus_minutes} мин\n"
        f"• Потолок: {cap_minutes} мин\n"
        f"• Активные роли: {enabled_roles}"
    )


@router.message(Command("ramp"))
@general.telegram_auth
async def command_ramp_handler(message: Message) -> None:
    """Handler for /ramp command showing status and reset button."""
    status = ramp.get_ramp_status()
    text = format_ramp_message(status)
    markup = get_ramp_keyboard()
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "ramp:reset")
async def process_ramp_reset(callback: CallbackQuery) -> None:
    """Callback query handler for resetting ramp to 1 min."""
    new_status = ramp.reset_ramp()
    await callback.answer("✅ Разгон сброшен на 1 мин")

    if not new_status or not isinstance(new_status, dict):
        new_status = {
            "current_step": 1,
            "today_focus_minutes": 0,
            "cap_minutes": 25,
            "config": {"enabled_roles": ["work", "learn"]},
        }
    elif "current_step" not in new_status:
        new_status["current_step"] = 1

    text = format_ramp_message(new_status)
    markup = get_ramp_keyboard()
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            pass
