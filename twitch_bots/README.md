# Twitch Bots

MeTuber hosts **Twitch bots and bot scaffolds** alongside webcam filters and virtual camera features.

## Layout

```
twitch_bots/
  scaffold/          # Starter template for new bots
  echo_bot/          # Minimal working example
```

## Quick start (echo bot)

```bash
cd D:\MeTuber
pip install -e .

# Copy and edit env template
copy twitch_bots\scaffold\.env.example .env

python -m twitch_bots.echo_bot
# or: metuber-echo-bot
```

## Creating a new bot

1. Copy `twitch_bots/scaffold/` to `twitch_bots/your_bot_name/`
2. Subclass `TwitchBotBase` from `twitch_bots.scaffold.base`
3. Implement `on_message()` and register commands
4. Add a `__main__.py` entry point

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWITCH_BOT_TOKEN` | Yes | OAuth token (`oauth:...`) |
| `TWITCH_CHANNEL` | Yes | Channel to join (lowercase) |
| `TWITCH_BOT_NICK` | Yes | Bot display name |
