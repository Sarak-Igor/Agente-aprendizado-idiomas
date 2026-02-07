from app.modules.language_learning.storage.cloze_store import save_cloze, get_cloze, cleanup_older_than
import time

def test_save_and_get_cloze():
    pid = "test-cloze-1"
    payload = {"id": pid, "answers": ["hello"], "masked": "____"}
    save_cloze(pid, payload)
    got = get_cloze(pid)
    assert got is not None
    assert got["id"] == pid
    assert got["answers"] == ["hello"]

def test_cleanup_removes_old():
    pid = "test-cloze-old"
    payload = {"id": pid, "answers": ["x"], "masked": "____"}
    save_cloze(pid, payload)
    # artificially wait and cleanup
    time.sleep(0.01)
    cleanup_older_than(seconds=0)
    got = get_cloze(pid)
    assert got is None

