#!/usr/bin/env python3
"""Minimal Telegram poller and file-based outgoing message sender.

Configuration is read from environment variables:
  TELEGRAM_QUEUE_DIR
  TELEGRAM_ALLOWED_USER_ID
  TELEGRAM_CHAT_ID

The bot token is read from ~/telegram-bot/token.
Uses only the Python standard library.
"""

import json
import os
import secrets
import string
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.environ["TELEGRAM_QUEUE_DIR"]).expanduser()
PENDING = BASE / "pending"
SENDMESSAGE = BASE / "sendmessage"
COMPLETED = BASE / "completed"
FAILED = BASE / "failed"

ALLOWED_USER_ID = int(os.environ["TELEGRAM_ALLOWED_USER_ID"])
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

TOKEN_FILE = Path.home() / "telegram-bot" / "token"
TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
if not TOKEN:
    raise RuntimeError(f"Telegram token file is empty: {TOKEN_FILE}")

API = f"https://api.telegram.org/bot{TOKEN}"

for directory in (PENDING, SENDMESSAGE, COMPLETED, FAILED):
    if not directory.is_dir():
        raise RuntimeError(f"Missing queue directory: {directory}")

def move_to_daily_folder(path, destination):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    folder = destination / day
    folder.mkdir(parents=True, exist_ok=True)
    os.replace(path, folder / path.name)

def telegram(method, data, timeout=40):
    """Call a fixed Telegram Bot API method."""
    request = urllib.request.Request(
        f"{API}/{method}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API call failed: {method}")
    return result["result"]


def atomic_write(path, data):
    """Write JSON to a temporary file, then atomically publish it."""
    temp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        with temp.open("x", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def task_exists(update_id):
    """Avoid duplicating an update if Telegram delivers it again."""
    for directory in (PENDING, COMPLETED, FAILED):
        for path in directory.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as file:
                    if json.load(file).get("update_id") == update_id:
                        return True
            except (OSError, ValueError, AttributeError):
                # Leave malformed files for inspection; do not trust their contents.
                continue
    return False


def new_task_path():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    alphabet = string.ascii_lowercase + string.digits
    # Four random characters, checking for an existing filename.
    for _ in range(100):
        suffix = "".join(secrets.choice(alphabet) for _ in range(4))
        path = PENDING / f"{timestamp}-{suffix}.json"
        if not path.exists():
            return path
    raise RuntimeError("Could not generate a unique task filename")


def receive_messages(offset):
    """Persist authorized text messages before advancing the polling offset."""
    updates = telegram(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message"],
        },
        timeout=40,
    )

    for update in updates:
        update_id = update["update_id"]
        message = update.get("message", {})
        sender = message.get("from", {})
        chat = message.get("chat", {})
        text = message.get("text")

        authorized = (
            sender.get("id") == ALLOWED_USER_ID
            and chat.get("id") == CHAT_ID
            and isinstance(text, str)
        )

        if authorized and not task_exists(update_id):
            path = new_task_path()
            task = {
                "task_id": path.stem,
                "update_id": update_id,
                "chat_id": CHAT_ID,
                "text": text,
                "created_at": message.get("date"),
            }
            # If this write fails, the function raises and the offset is not
            # advanced past this update; Telegram can deliver it again.
            atomic_write(path, task)
            print(f"Received task: {path.name}", flush=True)

        # Unauthorized/non-text updates are intentionally ignored.
        offset = update_id + 1

    return offset


def send_pending():
    """Try each outgoing JSON file once per polling iteration."""
    for path in sorted(SENDMESSAGE.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as file:
                task = json.load(file)

            tries = task.get("try_count", 0)
            text = task.get("text")

            if (
                not isinstance(tries, int)
                or isinstance(tries, bool)
                or tries < 0
                or not isinstance(text, str)
                or not text
                or len(text) > 4096
            ):
                move_to_daily_folder(path, FAILED)
                print(f"Invalid outgoing task moved to failed: {path.name}", flush=True)
                continue

            # As requested: if try_count is already 3, fail it without sending.
            if tries >= 3:
                os.replace(path, FAILED / path.name)
                print(f"Retry limit reached: {path.name}", flush=True)
                continue

            try:
                telegram(
                    "sendMessage",
                    {"chat_id": CHAT_ID, "text": text},
                    timeout=15,
                )
            except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
                task["try_count"] = tries + 1
                atomic_write(path, task)
                print(
                    f"Send failed for {path.name}; try_count={task['try_count']}: {error}",
                    flush=True,
                )
                # Leave it in sendmessage/. If count is now 3, the next
                # polling iteration moves it to failed/, per the agreed policy.
            else:
                move_to_daily_folder(path, COMPLETED)
                print(f"Sent message: {path.name}", flush=True)

        except (OSError, ValueError, TypeError, KeyError) as error:
            print(f"Could not process {path.name}: {error}", flush=True)


def main():
    offset = 0
    while True:
        try:
            offset = receive_messages(offset)
        except Exception as error:
            print(f"Polling failed; will retry: {error}", flush=True)
            time.sleep(5)

        send_pending()


if __name__ == "__main__":
    main()

