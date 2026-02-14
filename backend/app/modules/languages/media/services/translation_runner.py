import logging
from typing import Optional
from uuid import UUID

from app.modules.languages.media.services.youtube_service import YouTubeService
from app.models.database import Video, Translation, Job
from app.modules.languages.media.services.translation_orchestrator import select_translation_service
from app.modules.language_learning.persistence.checkpoint_utils import save_checkpoint, clear_checkpoint
from app.modules.languages.media.services.job_manager import JobManager

logger = logging.getLogger(__name__)


def run_translation_job(db, job_id: UUID, user_id: UUID, youtube_url: str, source_language: str, target_language: str, gemini_api_key: Optional[str]):
    jm = JobManager(db)
    try:
        jm.update_job(job_id, "processing", 10, "Extraindo legenda do YouTube...")
        youtube_service = YouTubeService()
        video_id = youtube_service.extract_video_id(youtube_url)

        video = db.query(Video).filter(Video.youtube_id == video_id, Video.user_id == user_id).first()
        if not video:
            video_info = youtube_service.get_video_info(video_id)
            video = Video(user_id=user_id, youtube_id=video_id, title=video_info.get("title"), duration=video_info.get("duration"))
            db.add(video)
            db.commit()
            db.refresh(video)
        else:
            if not video.title:
                video_info = youtube_service.get_video_info(video_id)
                if video_info.get("title"):
                    video.title = video_info.get("title")
                if video_info.get("duration") and not video.duration:
                    video.duration = video_info.get("duration")
                db.commit()

        job = jm.get_job(job_id)
        if job:
            job.video_id = video.id
            db.commit()

        jm.update_job(job_id, "processing", 30, "Buscando legendas...")
        segments = youtube_service.get_transcript(video_id, [source_language])
        if not segments:
            raise Exception("Nenhuma legenda encontrada para este vídeo")

        jm.update_job(job_id, "processing", 50, f"Traduzindo {len(segments)} segmentos...")

        translation_service, selected_service_name, tried_services, last_error = select_translation_service(db, user_id, gemini_api_key)
        if not translation_service:
            raise Exception(f"Nenhum serviço de tradução disponível. Tentados: {', '.join(tried_services)}. Último erro: {last_error}")

        # progress callback
        def update_progress(progress, message):
            adjusted_progress = 50 + int((progress / 100) * 40)
            jm.update_job(job_id, "processing", adjusted_progress, message)

        is_gemini = (selected_service_name == "gemini" or hasattr(translation_service, "gemini_service") or type(translation_service).__name__ == "GeminiServiceAdapter")
        if is_gemini:
            def checkpoint_cb(group_index, translated_segments, blocked_models):
                save_checkpoint(jm.get_job(job_id), translated_segments, group_index, db)
            translated_segments = translation_service.translate_segments(
                segments,
                target_language,
                source_language,
                progress_callback=update_progress,
                checkpoint_callback=checkpoint_cb,
                start_from_index=0,
                existing_translations=None,
                max_gap=0.0
            )
        else:
            translated_segments = translation_service.translate_segments(
                segments,
                target_language,
                source_language,
                max_gap=0.0,
                progress_callback=update_progress
            )

        jm.update_job(job_id, "processing", 90, "Salvando tradução...")

        segments_json = [
            {"start": seg.start, "duration": seg.duration, "original": seg.original, "translated": seg.translated}
            for seg in translated_segments
        ]

        existing_translation = db.query(Translation).filter(
            Translation.video_id == video.id,
            Translation.user_id == user_id,
            Translation.source_language == source_language,
            Translation.target_language == target_language
        ).first()

        if existing_translation:
            existing_translation.segments = segments_json
        else:
            translation = Translation(user_id=user_id, video_id=video.id, source_language=source_language, target_language=target_language, segments=segments_json)
            db.add(translation)

        clear_checkpoint(jm.get_job(job_id), db)
        db.commit()
        jm.update_job(job_id, "completed", 100, "Tradução concluída com sucesso!")
    except Exception as e:
        error_str = str(e)
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower() or 'Cota excedida' in error_str:
            try:
                jm.update_job(job_id, "processing", None, f"Pausado: {error_str}. O progresso foi salvo e pode ser retomado.")
            except Exception:
                db.rollback()
            return
        else:
            try:
                jm.update_job(job_id, "error", message=f"Erro no processamento", error=error_str)
            except Exception:
                db.rollback()
            raise

