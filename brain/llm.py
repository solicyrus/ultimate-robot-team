"""ULTIMATE ROBOT TEAM — brain/llm.py

Real AI thinking for the team. Every "smart" robot calls this module —
nothing here is simulated.

- The API key comes ONLY from the OPENAI_API_KEY environment variable.
  It is NEVER stored in this repo (.env is gitignored).
- Model: gpt-4o-mini, a few hundred tokens per call (~$0.001-0.003).
- ask()      -> (text, True)  on success, (None, False) on ANY failure.
- ask_json() -> (dict, True)  on success, (None, False) on ANY failure.
- NEVER raises. NEVER prints or logs the key.
- No key / no network / bad response  =>  clean (None, False) so the
  caller can report an honest failure instead of faking a result.
"""

import json
import os

MODEL = "gpt-4o-mini"


def _client():
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=key, timeout=30)


def ask(prompt, system, max_tokens=600, temperature=0.7):
    """Ask the AI for free-form text.

    Returns (text, True) on success, (None, False) on any failure.
    Never raises.
    """
    client = _client()
    if client is None:
        return None, False
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return None, False
        return text, True
    except Exception:
        return None, False


def ask_json(prompt, system, max_tokens=800, temperature=0.5):
    """Ask the AI for a JSON object.

    Returns (dict, True) on success, (None, False) on any failure.
    Never raises.
    """
    text, ok = ask(prompt, system, max_tokens=max_tokens,
                   temperature=temperature)
    if not ok or not text:
        return None, False
    try:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None, False
        data = json.loads(text[start:end + 1])
        if not isinstance(data, dict):
            return None, False
        return data, True
    except Exception:
        return None, False
