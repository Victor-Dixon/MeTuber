---
title: Twitch Bots Product Requirements Document
repository: D:\MeTuber
status: Draft
version: 1.0
last_updated: 2026-06-10
x-standard-prd: v1
---

## Overview

Twitch bots and bot scaffolds for streamers, hosted in the canonical MeTuber repo alongside webcam/filter tooling.

## Problem Statement

- StreamerTools previously duplicated MeTuber webcam code, causing confusion and drift.
- Operators need one repo for streaming tooling: video filters, virtual camera, and Twitch automation.

## Goals

- Ship a maintainable, test-backed Twitch bot capability under `twitch_bots/`.
- Keep docs aligned with the unified MeTuber project.

## Requirements

### Functional

- Host Twitch bot scaffolds under `twitch_bots/`.
- Provide a working echo bot example with IRC command handling (`!ping`, `!echo`).
- Webcam/filter features remain in the main MeTuber application.

### Non-Functional

- Test-backed changes where applicable.
- No secrets committed (use `.env` from `.env.example`).

## Success Metrics

- `python -m twitch_bots.echo_bot` runs with valid credentials.
- Unit tests pass for scaffold parsing and command registration.
