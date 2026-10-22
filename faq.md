# Telegram Bot Daemon: Troubleshooting FAQ

Run these commands from your everyday Mac account. Use `sudo` for daemon operations.

## 1. Is the daemon running?

```bash
sudo launchctl print system/com.local.telegrambot
```

Look for `state = running` and the process PID.

If it is not running, restart it:
And do this when bot.py changes

```bash
sudo launchctl kickstart -k system/com.local.telegrambot
```

## 2. Where are the logs?

```bash
tail -100 /Users/telegrambot/telegram-bot/bot.log
tail -100 /Users/telegrambot/telegram-bot/bot-error.log
```

Follow logs live:

```bash
tail -f /Users/telegrambot/telegram-bot/bot.log \
        /Users/telegrambot/telegram-bot/bot-error.log
```

## 3. How do I restart the daemon?

```bash
sudo launchctl kickstart -k system/com.local.telegrambot
```

The `-k` option terminates the existing process before restarting it.

## 4. What if I change `bot.py` or `run.py`?

Restart the daemon to load the changes:

```bash
sudo launchctl kickstart -k system/com.local.telegrambot
```

You do not need to reload the plist unless you change its configuration.

## 5. What if I change the plist?

Validate and reload it:

```bash
sudo plutil -lint /Library/LaunchDaemons/com.local.telegrambot.plist

sudo launchctl bootout system/com.local.telegrambot
sudo launchctl bootstrap system /Library/LaunchDaemons/com.local.telegrambot.plist
```

## 6. What if the daemon is not loaded?

Check:

```bash
sudo launchctl print system/com.local.telegrambot
```

If the service does not exist, bootstrap it:

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.local.telegrambot.plist
```

## 7. What if it keeps restarting or fails immediately?

Check the error log and configuration:

```bash
sudo plutil -lint /Library/LaunchDaemons/com.local.telegrambot.plist

ls -l /Users/telegrambot/telegram-bot/{bot.py,run.py,token,config.env}
```

Common causes include invalid Python code, missing environment variables, unreadable files, and incorrect queue permissions.

## 8. What if the Mac sleeps?

The bot cannot poll Telegram while the Mac sleeps. It should resume when the Mac wakes. Check the logs and daemon status if it does not.

## 9. What if the bot stops after a crash?

The plist has `KeepAlive = true`, so `launchd` should restart the process automatically. If it does not, use the status and restart commands above.

## 10. How do I disable or re-enable it?

Stop and unload:

```bash
sudo launchctl bootout system/com.local.telegrambot
```

Re-enable:

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.local.telegrambot.plist
```

## Quick recovery checklist

1. Check daemon status.
2. Inspect `bot-error.log`.
3. Restart with `kickstart`.
4. Verify a Telegram message is received.
5. Check task queue permissions.

> **Important:** `KeepAlive` restarts the process, but it does not guarantee the bot is functioning correctly. Periodically test the incoming and outgoing flows, especially after macOS or Python updates.

