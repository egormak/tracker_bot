import logging
from typing import Callable, Iterable

from aiogram.types import CallbackQuery

from keyboards.callback import task_hash, HASH_MARKER
from tracker import timer, stats

logger = logging.getLogger(__name__)


def known_task_names() -> list[str]:
    names = []
    try:
        names += [t.get("task_name", "") for t in timer.TimerList()]
    except Exception:
        pass
    try:
        names += [t.get("name") or t.get("task_name", "") for t in stats.GetTaskList()]
    except Exception:
        pass
    return [n for n in names if n]


def try_resolve_task_token(raw: str, extra_names: Callable[[], Iterable[str]] | None = None) -> str | None:
    """Maps a callback payload back to a task name. Payloads are the task name itself,
    or `#<sha1[:12]>` when the name was too long for Telegram's 64-byte callback limit.
    `extra_names` supplies additional candidates (e.g. evening focus tasks) checked first.
    Returns None when a hash payload matches no known task."""
    if not (raw.startswith(HASH_MARKER) and len(raw) == len(HASH_MARKER) + 12):
        return raw
    digest = raw[len(HASH_MARKER):]
    sources = ([extra_names] if extra_names else []) + [known_task_names]
    is_literal_name = False
    for source in sources:
        try:
            names = list(source())
        except Exception:
            continue
        for name in names:
            if name and task_hash(name) == digest:
                return name
        # A short task may itself be named like a hash payload.
        is_literal_name = is_literal_name or raw in names
    return raw if is_literal_name else None


async def answer_unknown_task(callback: CallbackQuery, hint: str) -> None:
    """Alerts that the button's hashed task name matches no task; the caller must not act on it."""
    try:
        await callback.answer(f"Задача не найдена. {hint}", show_alert=True)
    except Exception as e:
        logger.warning("Failed to answer callback for unknown task: %s", e)


def split_task_payload(callback_data: str, prefix: str) -> tuple[str, str]:
    """Splits `prefix<task>:<suffix>` from the right so task names containing ':' survive."""
    raw = callback_data[len(prefix):]
    if ":" in raw:
        task, suffix = raw.rsplit(":", 1)
        return task, suffix
    return raw, ""
