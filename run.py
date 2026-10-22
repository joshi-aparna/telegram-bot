import os
import runpy
from pathlib import Path

config = Path.home() / "telegram-bot" / "config.env"

for line in config.read_text().splitlines():
    line = line.strip()
    if line.startswith("export "):
        key, value = line[7:].split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")

runpy.run_path(
    str(Path.home() / "telegram-bot" / "bot.py"),
    run_name="__main__",
)
