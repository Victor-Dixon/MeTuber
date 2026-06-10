"""Run the echo bot: `python -m twitch_bots.echo_bot`."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitch_bots.echo_bot.bot import EchoBot


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    bot = EchoBot()
    bot.run()


if __name__ == "__main__":
    main()
