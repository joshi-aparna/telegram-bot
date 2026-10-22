
import json
import os
import urllib.request
from pathlib import Path

home = Path.home()
token = (home / "telegram-bot" / "token").read_text().strip()
config = home / "telegram-bot" / "config.env"

request = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/getUpdates"
)

with urllib.request.urlopen(request, timeout=15) as response:
    data = json.load(response)

if not data.get("ok"):
    raise RuntimeError("Telegram API request failed")

# Find the latest private-chat message.
for update in reversed(data["result"]):
    message = update.get("message", {})
    chat = message.get("chat", {})
    sender = message.get("from", {})

    if chat.get("type") == "private" and sender.get("id"):
        user_id = sender["id"]
        chat_id = chat["id"]
        break
else:
    raise RuntimeError(
        "No private message found. Send /start to your bot, then retry."
    )

content = (
    f'export TELEGRAM_QUEUE_DIR="/Users/Shared/taskqueue"\n'
    f'export TELEGRAM_ALLOWED_USER_ID="{user_id}"\n'
    f'export TELEGRAM_CHAT_ID="{chat_id}"\n'
)

config.write_text(content)
os.chmod(config, 0o600)

print(f"Configuration written to {config}")
print("Permissions set to 600.")

