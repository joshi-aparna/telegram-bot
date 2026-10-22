#!/bin/bash
set -euo pipefail

# Install the Telegram bot as a system LaunchDaemon.
# Run this script from your everyday macOS account with sudo access.

BOT_USER="telegrambot"
BOT_GROUP="staff"
BOT_DIR="/Users/${BOT_USER}/telegram-bot"
RUN_SCRIPT="${BOT_DIR}/run.py"
PLIST_LABEL="com.local.telegrambot"
PLIST_SOURCE="$(mktemp "/tmp/${PLIST_LABEL}.XXXXXX.plist")"
trap 'rm -f "${PLIST_SOURCE}"' EXIT
PLIST_DEST="/Library/LaunchDaemons/${PLIST_LABEL}.plist"
PYTHON="/usr/local/bin/python3"

if [[ "${EUID}" -eq 0 ]]; then
    echo "Do not run this script with sudo. Run it as your normal account."
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "Error: sudo is required."
    exit 1
fi

if [[ ! -f "${RUN_SCRIPT}" ]]; then
    echo "Error: ${RUN_SCRIPT} not found."
    exit 1
fi

if [[ ! -f "${BOT_DIR}/config.env" || ! -f "${BOT_DIR}/token" ]]; then
    echo "Error: config.env and token must exist in ${BOT_DIR} before installation."
    exit 1
fi

if [[ ! -x "${PYTHON}" ]]; then
    echo "Error: Python was not found at ${PYTHON}."
    echo "Update PYTHON in this script to the path of the Python interpreter used by run.py."
    exit 1
fi

cat > "${PLIST_SOURCE}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${RUN_SCRIPT}</string>
    </array>

    <key>UserName</key>
    <string>${BOT_USER}</string>

    <key>GroupName</key>
    <string>${BOT_GROUP}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/${BOT_USER}</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>${BOT_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>${BOT_DIR}/bot.log</string>

    <key>StandardErrorPath</key>
    <string>${BOT_DIR}/bot-error.log</string>
</dict>
</plist>
PLIST

plutil -lint "${PLIST_SOURCE}"

echo "Installing LaunchDaemon plist..."
sudo install -o root -g wheel -m 644 "${PLIST_SOURCE}" "${PLIST_DEST}"

echo "Reloading LaunchDaemon..."
if sudo launchctl print "system/${PLIST_LABEL}" >/dev/null 2>&1; then
    sudo launchctl bootout "system/${PLIST_LABEL}"
fi
sudo launchctl bootstrap system "${PLIST_DEST}"
sudo launchctl enable "system/${PLIST_LABEL}"

echo "LaunchDaemon installed."
echo "Check status with:"
echo "  sudo launchctl print system/${PLIST_LABEL}"
echo "View logs with:"
echo "  tail -100 ${BOT_DIR}/bot.log ${BOT_DIR}/bot-error.log"

