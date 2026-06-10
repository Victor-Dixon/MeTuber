"""Echo bot — replies to !ping and logs chat."""

from __future__ import annotations

import logging

from twitch_bots.scaffold.base import TwitchBotBase

logger = logging.getLogger(__name__)


class EchoBot(TwitchBotBase):
    def on_ready(self) -> None:
        self.register_command("ping", self._cmd_ping)
        self.register_command("echo", self._cmd_echo)
        self.send_message("Echo bot online. Try !ping or !echo <text>")

    def on_message(self, user: str, message: str) -> None:
        logger.info("<%s> %s", user, message)

    def _cmd_ping(self, user: str, _args: str) -> None:
        self.send_message(f"Pong, @{user}!")

    def _cmd_echo(self, user: str, args: str) -> None:
        if not args:
            self.send_message(f"@{user} usage: !echo <message>")
            return
        self.send_message(args)
