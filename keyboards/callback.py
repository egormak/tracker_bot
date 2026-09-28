import hashlib

# Telegram rejects the whole message if any button's callback_data exceeds 64 bytes.
MAX_CALLBACK_BYTES = 64
HASH_MARKER = "#"


def task_hash(task_name: str) -> str:
    return hashlib.sha1(task_name.encode("utf-8")).hexdigest()[:12]


def task_callback(prefix: str, task_name: str, suffix: str = "") -> str:
    """Builds `prefix:task_name[suffix]`, falling back to `prefix:#<sha1[:12]>[suffix]`
    when the name would push the payload past Telegram's 64-byte limit.
    Must stay in sync with tracker-server's internal/notify/telegram callbackData."""
    data = f"{prefix}:{task_name}{suffix}"
    if len(data.encode("utf-8")) <= MAX_CALLBACK_BYTES:
        return data
    return f"{prefix}:{HASH_MARKER}{task_hash(task_name)}{suffix}"
