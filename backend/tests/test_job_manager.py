from types import SimpleNamespace
from uuid import uuid4
from app.modules.language_learning.services.job_manager import JobManager


class FakeSession:
    def __init__(self):
        self.storage = {}

    def add(self, obj):
        # assign id if missing
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        self.storage[obj.id] = obj

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass

    def query(self, model):
        class Q:
            def __init__(self, storage):
                self.storage = storage

            def filter(self, *args, **kwargs):
                # naive: return first stored
                class F:
                    def __init__(self, storage):
                        self.storage = storage

                    def first(self):
                        return next(iter(self.storage.values())) if self.storage else None
                return F(self.storage)
        return Q(self.storage)


def test_create_and_get_job():
    session = FakeSession()
    jm = JobManager(session)
    job = jm.create_job(uuid4())
    assert job is not None
    assert getattr(job, "id", None) in session.storage

def test_update_job():
    session = FakeSession()
    jm = JobManager(session)
    user_id = uuid4()
    job = jm.create_job(user_id)
    updated = jm.update_job(job.id, "processing", 10, "msg")
    assert updated.status == "processing"
    assert updated.progress == 10
    assert updated.message == "msg"

