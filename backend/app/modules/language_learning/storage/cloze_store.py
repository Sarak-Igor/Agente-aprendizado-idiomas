from typing import Dict, Any
import threading
import time

# Simple in-memory store for generated cloze exercises.
# Keys: phrase_id -> {payload, created_at}
_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def save_cloze(phrase_id: str, payload: Dict[str, Any]) -> None:
    with _lock:
        _store[phrase_id] = {"payload": payload, "created_at": time.time()}

def get_cloze(phrase_id: str) -> Dict[str, Any]:
    with _lock:
        item = _store.get(phrase_id)
        if not item:
            return None
        return item["payload"]

def cleanup_older_than(seconds: int = 3600):
    cutoff = time.time() - seconds
    with _lock:
        to_delete = [k for k, v in _store.items() if v["created_at"] < cutoff]
        for k in to_delete:
            del _store[k]

