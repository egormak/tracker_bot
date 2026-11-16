"""Quick controls: the persistent main keyboard, the task grid with a duration card,
"close the debt" starts, the "Сегодня" and "Долг" cards and starting a task by typing its name."""
import logging
import re

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from tracker import general, stats, timer, evening, errors
from tracker import debt as debt_api
from keyboards import quick as kb
from keyboards.timer import get_running_timer_keyboard
from handlers.task_callback import try_resolve_task_token, answer_unknown_task, split_task_payload
from handlers import timer as timer_handler

logger = logging.getLogger(__name__)

router = Router()

DEBT_WORDS = {"долг", "debt"}
MINUTES_RE = re.compile(r"(\d{1,3})(м|m|мин|min)?")
SHARE_RE = re.compile(r"(\d{1,3})%")
FULL_SHARE = 100
TEXT_HINT = "Можно написать текстом: «video 30», «video 60 50%», «video долг»."


# --- data ---


def _safe_debt() -> dict:
    try:
        return debt_api.GetDebt()
    except Exception as e:
        logger.warning("Failed to get debt: %s", e)
        return {}


def _today_tasks() -> list[dict]:
    try:
        return stats.GetTaskList() or []
    except Exception as e:
        logger.warning("Failed to get task list: %s", e)
        return []


def _task_name(task: dict) -> str:
    return task.get("name") or task.get("task_name") or ""


def collect_tasks(today: list[dict], debt_by_task: dict[str, int]) -> list[tuple[str, int]]:
    """Grid order: tasks with minutes left today, then tasks that only have debt, then finished ones."""
    open_tasks, done_tasks, seen = [], [], set()
    for task in today:
        name = _task_name(task)
        if not name or name in seen:
            continue
        seen.add(name)
        remaining = stats.TaskRemaining(task)
        (open_tasks if remaining > 0 else done_tasks).append((name, remaining))
    debt_only = [(name, 0) for name in debt_by_task if name not in seen]
    return open_tasks + debt_only + done_tasks


def parse_quick_text(text: str, names: list[str]) -> tuple[str, int, int] | None:
    """Returns (name, minutes, debt share %). `video` → (video, 0, 0); `video 30` → (video, 30, 0);
    `video долг` / `video в долг` → (video, 0, 100); `video 20 долг` → (video, 20, 100);
    `video 60 50%` → (video, 60, 50). The name matches case-insensitively; None when it matches
    no known task."""
    tokens = (text or "").strip().split()
    minutes, share = 0, 0
    while tokens:
        tail = tokens[-1].lower()
        match = MINUTES_RE.fullmatch(tail)
        if match and not minutes and int(match.group(1)) > 0:
            minutes = int(match.group(1))
            tokens.pop()
            continue
        match = SHARE_RE.fullmatch(tail)
        if match and not share and 0 < int(match.group(1)) <= FULL_SHARE:
            share = int(match.group(1))
            tokens.pop()
            continue
        if tail in DEBT_WORDS and not share:
            share = FULL_SHARE
            tokens.pop()
            if tokens and tokens[-1].lower() == "в":
                tokens.pop()
            continue
        break
    wanted = " ".join(tokens).lower()
    if not wanted:
        return None
    for name in names:
        if name and name.lower() == wanted:
            return name, minutes, share
    return None


def start_task(task_name: str, minutes: int, share: int) -> tuple[bool, str]:
    """Starts `task_name` for `minutes`; `share` % of the session pays its previous-days debt."""
    try:
        res = timer.TimerStart(task_name, target_duration=minutes, debt_share=share)
    except Exception:
        logger.exception("Failed to start '%s'", task_name)
        return False, "Не удалось запустить: сервер недоступен."
    if res.startswith("Failed"):
        return False, res
    if share >= FULL_SHARE:
        return True, f"💳 {task_name} — {minutes} мин в счёт долга"
    if share > 0:
        return True, f"▶️ {task_name} — {minutes} мин, 💳 {share}% в долг"
    return True, f"▶️ {task_name} — {minutes} мин"


# --- rendering ---


async def _reply(message: Message, text: str, markup: InlineKeyboardMarkup | None, edit: bool) -> None:
    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
            return
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return
            logger.warning("Failed to edit message, sending a new one: %s", e)
    await message.answer(text, reply_markup=markup)


async def send_tasks(message: Message, edit: bool = False) -> None:
    try:
        today = stats.GetTaskList() or []
    except errors.InvalidStatusCode as e:
        await _reply(message, e.message, None, edit)
        return
    except Exception as e:
        await _reply(message, f"Не удалось получить задачи: {e}", None, edit)
        return
    debt_by_task = debt_api.DebtByTask(_safe_debt())
    tasks = collect_tasks(today, debt_by_task)
    if tasks:
        text = f"▶️ Что запустить?\nЧисло — осталось сегодня, 💳 — долг прошлых дней.\n{TEXT_HINT}"
    else:
        text = f"На сегодня задач нет.\n{TEXT_HINT}"
    await _reply(message, text, kb.get_task_grid_keyboard(tasks, debt_by_task), edit)


def format_task_card(name: str, today_task: dict | None, debt: int) -> str:
    lines = [f"▶️ {name}"]
    if today_task is None:
        lines.append("Сегодня: нет в расписании")
    else:
        remaining = stats.TaskRemaining(today_task)
        done, planned = today_task.get("time_done", 0), today_task.get("time_duration", 0)
        status = f"осталось {remaining}м" if remaining > 0 else "план выполнен"
        lines.append(f"Сегодня: {done}/{planned}м — {status}")
    if debt > 0:
        lines.append(f"💳 Долг прошлых дней: {debt}м")
        if today_task is not None and stats.TaskRemaining(today_task) > 0:
            total = stats.TaskRemaining(today_task) + debt
            lines.append(f"💳 % — запуск на {total}м: эта доля уходит в долг, остальное в сегодня")
    lines.append("\nНа сколько минут?")
    return "\n".join(lines)


async def send_today(message: Message, edit: bool = False) -> None:
    try:
        state = stats.GetDashboardState()
    except errors.InvalidStatusCode as e:
        await _reply(message, e.message, None, edit)
        return
    except Exception as e:
        await _reply(message, f"Не удалось получить статистику: {e}", None, edit)
        return
    text = stats.FormatToday(state, _safe_debt().get("total_minutes", 0))
    await _reply(message, text, kb.get_today_keyboard(), edit)


async def send_debt(message: Message, edit: bool = False) -> None:
    try:
        debt = debt_api.GetDebt()
    except errors.InvalidStatusCode as e:
        await _reply(message, e.message, None, edit)
        return
    except Exception as e:
        await _reply(message, f"Не удалось получить долг: {e}", None, edit)
        return
    await _reply(message, debt_api.FormatDebt(debt), kb.get_debt_keyboard(debt_api.DebtByTask(debt)), edit)


async def send_now(message: Message) -> None:
    try:
        active = timer.TimerList()
    except Exception:
        active = []
    if not active:
        await message.answer("Сейчас ничего не идёт.", reply_markup=kb.get_idle_keyboard())
        return
    await timer_handler.send_timer_status(message)


# --- main keyboard buttons and commands ---
# Registered before the free-text handler below, and this router comes first in main.py, so the
# buttons also work while another command waits for input (the state is cleared).


@router.message(Command("menu"))
@general.telegram_auth_with_state
async def command_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(f"Кнопки внизу.\n{TEXT_HINT}", reply_markup=kb.get_main_keyboard())


@router.message(F.text == kb.MAIN_TASKS)
@router.message(Command("go"))
@general.telegram_auth_with_state
async def main_tasks(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_tasks(message)


@router.message(F.text == kb.MAIN_NOW)
@router.message(Command("now"))
@general.telegram_auth_with_state
async def main_now(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_now(message)


@router.message(F.text == kb.MAIN_TODAY)
@router.message(Command("today"))
@general.telegram_auth_with_state
async def main_today(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_today(message)


@router.message(F.text == kb.MAIN_DEBT)
@router.message(Command("debt"))
@general.telegram_auth_with_state
async def main_debt(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_debt(message)


# --- callbacks ---


def _debt_names() -> list[str]:
    return list(debt_api.DebtByTask(_safe_debt()))


@router.callback_query(F.data == kb.TASKS_DATA)
async def process_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_tasks(callback.message, edit=True)


@router.callback_query(F.data == kb.TODAY_DATA)
async def process_today(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_today(callback.message, edit=True)


@router.callback_query(F.data == kb.DEBTS_DATA)
async def process_debts(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_debt(callback.message, edit=True)


@router.callback_query(F.data.startswith(f"{kb.TASK_CARD_PREFIX}:"))
async def process_task_card(callback: CallbackQuery) -> None:
    name = try_resolve_task_token(callback.data[len(kb.TASK_CARD_PREFIX) + 1:], extra_names=_debt_names)
    if name is None:
        await answer_unknown_task(callback, "Откройте ▶️ Задачи заново")
        return
    await callback.answer()
    today_task = next((t for t in _today_tasks() if _task_name(t) == name), None)
    debt = debt_api.DebtByTask(_safe_debt()).get(name, 0)
    remaining = stats.TaskRemaining(today_task) if today_task else 0
    await _reply(
        callback.message,
        format_task_card(name, today_task, debt),
        kb.get_task_card_keyboard(name, remaining, debt),
        edit=True,
    )


async def _start_from_callback(callback: CallbackQuery, prefix: str, share: int | None) -> None:
    """`share` None means the share comes from the payload (`<min>-<pct>`)."""
    token, payload = split_task_payload(callback.data, f"{prefix}:")
    name = try_resolve_task_token(token, extra_names=_debt_names)
    if name is None:
        await answer_unknown_task(callback, "Откройте ▶️ Задачи заново")
        return
    min_str = payload
    if share is None:
        min_str, _, pct_str = payload.partition("-")
        share = min(int(pct_str), FULL_SHARE) if pct_str.isdigit() else 0
    minutes = int(min_str) if min_str.isdigit() and int(min_str) > 0 else stats.DEFAULT_START_MINUTES
    ok, text = start_task(name, minutes, share)
    if not ok:
        # The keyboard stays: nothing started, the user can tap again.
        await callback.answer(text, show_alert=True)
        return
    await callback.answer(text)
    await _reply(callback.message, text, get_running_timer_keyboard(name), edit=True)


@router.callback_query(F.data.startswith(f"{kb.GO_PREFIX}:"))
async def process_go(callback: CallbackQuery) -> None:
    await _start_from_callback(callback, kb.GO_PREFIX, share=0)


@router.callback_query(F.data.startswith(f"{kb.DEBT_PREFIX}:"))
async def process_debt_start(callback: CallbackQuery) -> None:
    await _start_from_callback(callback, kb.DEBT_PREFIX, share=FULL_SHARE)


@router.callback_query(F.data.startswith(f"{kb.SHARE_PREFIX}:"))
async def process_share_start(callback: CallbackQuery) -> None:
    await _start_from_callback(callback, kb.SHARE_PREFIX, share=None)


# --- free text: "video 30", "video долг" ---
# Only outside any FSM state, so the input of /timer_start and /taskrecordadd is left alone.


@router.message(StateFilter(default_state), F.text, ~F.text.startswith("/"))
@general.telegram_auth
async def quick_text_start(message: Message) -> None:
    debt_by_task = debt_api.DebtByTask(_safe_debt())
    names = [_task_name(t) for t in _today_tasks()] + list(debt_by_task)
    parsed = parse_quick_text(message.text, names)
    if parsed is None:
        try:
            names += [o.get("task_name", "") for o in evening.get_break_options().get("options", [])]
        except Exception as e:
            logger.warning("Failed to get break options: %s", e)
        parsed = parse_quick_text(message.text, names)
    if parsed is None:
        await message.answer(
            f"Не нашёл задачу «{message.text.strip()}». Нажми {kb.MAIN_TASKS} или напиши, например: video 30, video долг.",
            reply_markup=kb.get_main_keyboard(),
        )
        return

    name, minutes, share = parsed
    task_debt = debt_by_task.get(name, 0)
    if share and not minutes:
        if not task_debt:
            await message.answer(f"У {name} нет долга.")
            return
        if share >= FULL_SHARE:
            minutes = task_debt
        else:
            # A partial share without minutes covers today's remainder and the whole debt.
            today_task = next((t for t in _today_tasks() if _task_name(t) == name), None)
            minutes = (stats.TaskRemaining(today_task) if today_task else 0) + task_debt
    if not minutes:
        minutes = stats.StartTarget(name)
    ok, text = start_task(name, minutes, share)
    await message.answer(text, reply_markup=get_running_timer_keyboard(name) if ok else None)
