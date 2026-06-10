# StreamerTools → MeTuber Merge

**Date:** 2026-06-10

## Summary

`D:\Streamertools` and `D:\MeTuber` are consolidated into **MeTuber** as the single canonical project.

StreamerTools had already removed its duplicate MeTuber webcam subtree (see `CLEANUP_NOTES.md` from the deprecated repo). This merge ports the remaining unique StreamerTools assets into MeTuber.

## What was merged from StreamerTools

| Asset | Destination | Notes |
|-------|-------------|-------|
| `twitch_bots/` | `twitch_bots/` | IRC scaffold + echo bot |
| `Transcripts/` | `Transcripts/` | Stream transcript archives |
| `setup.py` entry points | `setup.py` | `metuber-echo-bot` console script |
| Twitch PRD | `docs/twitch-bots-prd.md` | Bot-specific requirements |
| Roadmap notes | This document | StreamerTools roadmap absorbed |

## Intentionally not duplicated

- MeTuber webcam/filter code (already canonical in MeTuber)
- StreamerTools `config.json` (MeTuber has its own app config)
- Empty `requirements.txt` from StreamerTools (bots use stdlib only)

## Deprecated repo

- **Local:** `D:\Streamertools` (delete after verification)
- **Remote:** `https://github.com/Dadudekc/Streamertools.git`

## Twitch bots quick start

```bash
cd D:\MeTuber
pip install -e .

copy twitch_bots\scaffold\.env.example .env
# Edit .env with TWITCH_BOT_TOKEN, TWITCH_CHANNEL, TWITCH_BOT_NICK

python -m twitch_bots.echo_bot
# or: metuber-echo-bot
```
