"""Unit tests for Twitch bot scaffold (no network)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from twitch_bots.scaffold.base import TwitchBotBase


class _StubBot(TwitchBotBase):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.messages: list[str] = []

    def on_message(self, user: str, message: str) -> None:
        self.messages.append(f"{user}:{message}")

    def send_message(self, message: str) -> None:
        self.messages.append(f"sent:{message}")


@pytest.fixture
def bot_env():
    env = {
        "TWITCH_BOT_TOKEN": "oauth:test",
        "TWITCH_CHANNEL": "testchannel",
        "TWITCH_BOT_NICK": "testbot",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


def test_missing_credentials_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="TWITCH_BOT_TOKEN"):
            _StubBot()


def test_register_and_dispatch_command(bot_env):
    bot = _StubBot()
    replies: list[str] = []

    def ping_handler(user: str, _args: str) -> None:
        replies.append(user)

    bot.register_command("ping", ping_handler)
    bot._handle_line(":viewer!x@x.tmi.twitch.tv PRIVMSG #testchannel :!ping")

    assert replies == ["viewer"]


def test_parse_privmsg(bot_env):
    bot = _StubBot()
    parsed = bot._parse_privmsg(":alice!a@a.tmi.twitch.tv PRIVMSG #chan :hello world")
    assert parsed == ("alice", "hello world")


def test_ping_pong(bot_env):
    bot = _StubBot()
    bot._socket = type("Sock", (), {"sendall": lambda self, data: None})()
    bot._handle_line("PING :tmi.twitch.tv")
    assert bot._socket is not None
