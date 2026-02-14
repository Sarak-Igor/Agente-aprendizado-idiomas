from sqlalchemy.orm import Session
from typing import Optional
from app.models.database import Job, Video, Translation, ApiKey
from app.schemas.schemas import SubtitleSegment, TranslationSegment
from app.modules.languages.media.services.youtube_service import YouTubeService
from app.modules.languages.media.services.translation_factory import TranslationServiceFactory
from app.services.encryption import encryption_service
from uuid import UUID
import json
import os


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, user_id: UUID, video_id: UUID = None) -> Job:
        """Cria um novo job"""
        job = Job(
            user_id=user_id,
            video_id=video_id,
            status="queued",
            progress=0,
            message="Aguardando processamento",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job(
        self,
        job_id: UUID,
        status: str,
        progress: int = None,
        message: str = None,
        error: str = None,
        translation_service: str = None,
    ):
        """Atualiza status de um job"""
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

    def get_job(self, job_id: UUID) -> Job:
        """Obtém um job pelo ID"""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def process_translation_job(
        self,
        job_id: UUID,
        user_id: UUID,
        youtube_url: str,
        source_language: str,
        target_language: str,
        gemini_api_key: Optional[str],
    ):
        """Delegate processing to translation_runner.run_translation_job."""
        from app.modules.languages.media.services.translation_runner import run_translation_job

        return run_translation_job(
            self.db, job_id, user_id, youtube_url, source_language, target_language, gemini_api_key
        )

