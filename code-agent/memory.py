import os
import json

MEMORY_DIR = "memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "state.json")

def load_memory():
    """وضعیت قبلی ایجنت را بارگیری می‌کند."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_memory(state):
    """وضعیت ایجنت را برای اجرای بعدی ذخیره می‌کند."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Could not save memory: {e}")
