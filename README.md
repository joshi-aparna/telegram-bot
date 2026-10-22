# Telegram Task Queue Bot

A lightweight Telegram bot that bridges Telegram messages and a local, file-based task queue.

The bot uses Python's standard library and runs under a dedicated, unprivileged macOS user. It does not use an LLM or execute shell commands.

## How it works

- **Incoming messages:** The bot polls Telegram using `getUpdates`. Text messages from the configured Telegram user and chat are written as JSON task files to `pending/`.
- **Outgoing messages:** The bot reads JSON files from `sendmessage/` and sends their text to the configured Telegram chat.
- **Successful sends:** Files move to `completed/`, organized by date.
- **Failed sends:** The bot increments `try_count` and leaves the file in `sendmessage/` for a later polling iteration. Files with `try_count >= 3` move to `failed/` on a subsequent iteration.
- **Background execution:** A macOS `launchd` LaunchDaemon runs the bot without requiring the `telegrambot` account to log in to the desktop and restarts it if the process exits.

## How the queue is organized

The queue is configured by `TELEGRAM_QUEUE_DIR` and is kept outside the Git repository.

```text
queue/
├── pending/
├── sendmessage/
├── completed/
│   └── YYYY-MM-DD/
└── failed/
    └── YYYY-MM-DD/
```

An outgoing message file in `sendmessage/` can look like:

```json
{
  "text": "Task completed!",
  "try_count": 0
}
```

The bot sends outgoing messages only to `TELEGRAM_CHAT_ID`; it does not trust a `chat_id` supplied by a queue file.

## Requirements

- macOS
- Python 3
- A Telegram bot token created through [@BotFather](https://t.me/BotFather)
- A dedicated, non-administrator macOS user for running the bot

No third-party Python packages are required.

## Configuration

The bot reads these environment variables:

- `TELEGRAM_QUEUE_DIR` — path to the shared queue directory
- `TELEGRAM_ALLOWED_USER_ID` — numeric Telegram user ID allowed to submit incoming tasks
- `TELEGRAM_CHAT_ID` — numeric Telegram chat ID used for outgoing messages

Store these in a private `config.env` file in the bot user's home directory. The bot token is stored separately in `~/telegram-bot/token`.

Example `config.env` (replace the example values locally):

```bash
export TELEGRAM_QUEUE_DIR="/Users/Shared/taskqueue"
export TELEGRAM_ALLOWED_USER_ID="YOUR_USER_ID"
export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
```

Restrict access to credentials and configuration:

```bash
chmod 600 ~/telegram-bot/config.env
chmod 600 ~/telegram-bot/token
```

You can also run this script to do the same:

Run the setup script as the `telegrambot` user:

```bash
python3 ~/telegram-bot/setup_config.py
```

The script reads the bot token from `~/telegram-bot/token`, discovers your Telegram user and chat IDs from recent bot updates, and creates `config.env` with the required environment variables. It sets file permissions to `600`.

Send a private message to your bot before running the script. Rerunning the script overwrites the existing `config.env`.

**Security:** Never commit `token` or `config.env` to Git. Ensure both files are included in `.gitignore`.



Load configuration before running manually:

```bash
source ~/telegram-bot/config.env
```

Do not commit `config.env`, `token`, or log files.

## Run manually

From the `telegrambot` account:

```bash
source ~/telegram-bot/config.env
python3 -u ~/telegram-bot/bot.py
```

Keep it in the foreground while testing. Stop it with `Ctrl+C`.

### Install the LaunchDaemon

From your everyday macOS account, run:

```bash
./setup_launchdaemon.sh
```

The script generates and validates the LaunchDaemon plist, installs it at `/Library/LaunchDaemons/com.local.telegrambot.plist`, and starts the service. It prompts for administrator privileges when needed.

Check the service status:

```bash
sudo launchctl print system/com.local.telegrambot
```

View logs:

```bash
tail -100 ~/../telegrambot/telegram-bot/bot.log
```

The bot runs as the unprivileged `telegrambot` user and restarts automatically if it exits. To apply changes to `run.py` or `bot.py`, restart the service:

```bash
sudo launchctl kickstart -k system/com.local.telegrambot
```


## Run as a macOS LaunchDaemon

The service plist is installed at:

```text
/Library/LaunchDaemons/com.local.telegrambot.plist
```

Useful commands from an administrator account:

Check status:

```bash
sudo launchctl print system/com.local.telegrambot
```

Restart after changing `bot.py` or `run.py`:

```bash
sudo launchctl kickstart -k system/com.local.telegrambot
```

View logs:

```bash
tail -100 /Users/telegrambot/telegram-bot/bot.log
tail -100 /Users/telegrambot/telegram-bot/bot-error.log
```

Validate the plist:

```bash
sudo plutil -lint /Library/LaunchDaemons/com.local.telegrambot.plist
```

The bot cannot poll while the Mac is asleep or powered off. It should resume when the Mac wakes.

## Security notes

- Run the bot as a dedicated, unprivileged macOS user.
- Keep the token private and rotate it if exposed.
- Only accept incoming messages from the configured Telegram user and chat IDs.
- Do not add arbitrary shell execution or dynamic code execution.
- Grant shared-queue access only to the accounts that need it.
- Network egress is not restricted in the current setup; a compromised process could potentially make other outbound connections.
- File-based queues are easy to inspect, but retries cannot guarantee exactly-once Telegram delivery. If Telegram accepts a message and the bot loses the response, a retry may create a duplicate.

