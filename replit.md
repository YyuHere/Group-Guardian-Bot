# Telegram Group Bot

A Python Telegram bot with mention-all, anti-link enforcement, and media retrieval for group chats.

## Run & Operate

- `python bot/main.py` — run the bot (requires `BOT_TOKEN` env var)
- Workflow: `Telegram Bot` — configured in Replit to run the bot via console

## Stack

- Python 3
- python-telegram-bot 21.9 (async, polling mode)

## Where things live

- `bot/main.py` — entire bot logic (handlers, admin checks, media store)
- `bot/requirements.txt` — Python dependencies

## Architecture decisions

- **In-memory user tracking**: `seen_users` dict stores user IDs/usernames since the bot joined. Resets on restart — acceptable for a Telegram bot.
- **In-memory media store**: `bot_data["media_store"]` keyed by chat_id stores photo/video file_ids since bot joined.
- **Single combined handler**: All non-command messages go through one handler that tracks users, stores media, and checks for links — avoids conflicting handler ordering.
- **HTML parse mode for mentions**: Users without a username get an inline HTML mention link (`tg://user?id=...`) instead of `@username`.
- **Chunk size 5**: `/all` sends mentions in groups of 5 per message to avoid spam.

## Product

- `/all` — Admin-only. Mentions every user the bot has seen, 5 per message.
- `/media` — Admin-only. Forwards all stored photos/videos from the group to the requesting admin's DM.
- Anti-link — Auto-deletes messages containing HTTP/HTTPS/www links from non-admins.

## User preferences

- Bot token via `os.getenv('BOT_TOKEN')` — safe to host on GitHub and Railway.
- Only admins can use `/all` and `/media`.

## Gotchas

- The bot must have **Delete Messages** permission in the group for anti-link to work.
- The bot must be an admin itself in the group for `/all` and anti-link to function.
- Media retrieval only covers messages received **after the bot joined** — Telegram's Bot API does not allow reading chat history.
- Users must have started a DM with the bot before it can send them media via `/media`.

## Pointers

- See the `pnpm-workspace` skill for workspace structure info (Node.js artifacts are separate)
