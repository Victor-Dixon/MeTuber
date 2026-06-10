"""Base class for Twitch IRC bots."""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TwitchBotBase(ABC):
    """Minimal Twitch IRC client scaffold.

    Subclass and implement `on_message` to handle chat events.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        channel: Optional[str] = None,
        nick: Optional[str] = None,
        host: str = "irc.chat.twitch.tv",
        port: int = 6667,
    ) -> None:
        self.token = token or os.environ.get("TWITCH_BOT_TOKEN", "")
        self.channel = (channel or os.environ.get("TWITCH_CHANNEL", "")).lstrip("#").lower()
        self.nick = nick or os.environ.get("TWITCH_BOT_NICK", "")
        self.host = host
        self.port = port

        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._commands: Dict[str, Callable[[str, str], None]] = {}

        if not self.token or not self.channel or not self.nick:
            raise ValueError(
                "TWITCH_BOT_TOKEN, TWITCH_CHANNEL, and TWITCH_BOT_NICK are required"
            )

    def register_command(self, name: str, handler: Callable[[str, str], None]) -> None:
        """Register a chat command handler. `name` should not include '!'."""
        self._commands[name.lower()] = handler

    def send_message(self, message: str) -> None:
        """Send a message to the joined channel."""
        if not self._socket:
            return
        payload = f"PRIVMSG #{self.channel} :{message}\r\n".encode("utf-8")
        self._socket.sendall(payload)

    def connect(self) -> None:
        """Connect and authenticate to Twitch IRC."""
        sock = socket.socket()
        sock.connect((self.host, self.port))
        sock.settimeout(30)
        self._socket = sock

        self._send(f"PASS {self.token}")
        self._send(f"NICK {self.nick}")
        self._send("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands")
        self._send(f"JOIN #{self.channel}")
        logger.info("Joined #%s as %s", self.channel, self.nick)

    def _send(self, payload: str) -> None:
        if not self._socket:
            raise RuntimeError("Not connected")
        self._socket.sendall(f"{payload}\r\n".encode("utf-8"))

    def _parse_privmsg(self, line: str) -> Optional[tuple[str, str]]:
        if "PRIVMSG" not in line:
            return None
        try:
            prefix, rest = line.split("PRIVMSG", 1)
            user = prefix.split("!", 1)[0].lstrip(":")
            _, message = rest.split(":", 1)
            return user, message.strip()
        except ValueError:
            return None

    def _handle_line(self, line: str) -> None:
        if line.startswith("PING"):
            self._send("PONG :tmi.twitch.tv")
            return

        parsed = self._parse_privmsg(line)
        if not parsed:
            return

        user, message = parsed
        if message.startswith("!"):
            command, _, args = message[1:].partition(" ")
            handler = self._commands.get(command.lower())
            if handler:
                handler(user, args.strip())
                return

        self.on_message(user, message)

    def run(self) -> None:
        """Blocking run loop."""
        self.connect()
        self._running = True
        self.on_ready()

        while self._running and self._socket:
            try:
                data = self._socket.recv(4096)
                if not data:
                    break
                for line in data.decode("utf-8", errors="ignore").split("\r\n"):
                    if line:
                        self._handle_line(line)
            except socket.timeout:
                continue
            except OSError as exc:
                logger.error("Socket error: %s", exc)
                break

        self.stop()

    def run_async(self) -> None:
        """Start the bot in a background thread."""
        self._thread = threading.Thread(target=self.run, name="twitch-bot", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def on_ready(self) -> None:
        """Called after the bot joins the channel."""

    @abstractmethod
    def on_message(self, user: str, message: str) -> None:
        """Handle a non-command chat message."""
