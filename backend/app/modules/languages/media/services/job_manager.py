from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from app.models.database import Job


class JobManager:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, user_id: UUID, video_id: UUID = None) -> Job:
        job = Job(
            user_id=user_id,
            video_id=video_id,
            status="queued",
            progress=0,
            message="Aguardando processamento"
        )
        self.db.add(job)
        self.db.commit()
        try:
            self.db.refresh(job)
        except Exception:
            # refresh may be not available in fake sessions used in tests
            pass
        return job

    def update_job(self, job_id: UUID, status: str, progress: int = None, message: str = None, error: str = None, translation_service: str = None):
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None

            job.status = status
            if progress is not None:
                job.progress = progress
            if message:
                job.message = message
            if error:
                job.error = error
            if translation_service:
                job.translation_service = translation_service

            self.db.commit()
            return job
        except Exception:
            self.db.rollback()
            raise

    def get_job(self, job_id: UUID) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == job_id).first()

