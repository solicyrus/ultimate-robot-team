"""ULTIMATE ROBOT TEAM — robots/telegram_publisher.py

REAL Telegram publishing via the official Bot API:
    POST https://api.telegram.org/bot<token>/sendMessage

Credentials come ONLY from environment variables:
    TELEGRAM_BOT_TOKEN  (from @BotFather on Telegram)
    TELEGRAM_CHAT_ID    (your channel/group/chat id)

- publish(text) returns {"ok": True, "message_id": ...} ONLY when
  Telegram really accepted the message.
- When the token/chat id is missing it returns
  {"ok": False, "skipped": True, "reason": ...} — a CLEAN SKIP.
  It never pretends a message was sent.
- Never raises. Never prints or logs the token.
"""

import json
import os
import urllib.request

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def publish(text, chat_id=None, token=None):
    """Send text to Telegram. Returns a real result dict, never raises."""
    token = (token if token is not None
             else os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
    chat_id = (chat_id if chat_id is not None
               else os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

    if not token or not chat_id:
        return {"ok": False, "skipped": True,
                "reason": ("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — "
                           "publish skipped, nothing was sent")}

    try:
        status, data = _post(_API.format(token=token),
                             {"chat_id": chat_id, "text": text})
        if status == 200 and data.get("ok"):
            return {"ok": True,
                    "message_id": data["result"].get("message_id"),
                    "chat_id": chat_id}
        return {"ok": False,
                "error": f"Telegram API refused: {data.get('description', data)}"}
    except Exception as e:  # never raise; report the real error
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
