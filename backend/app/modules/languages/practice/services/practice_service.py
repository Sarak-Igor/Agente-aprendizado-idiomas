import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.database import Translation, Video, User
from app.modules.languages.practice.utils.text_similarity import (
    check_answer_similarity,
    calculate_similarity
)
from app.modules.agents.core_llm.services.orchestrator.router import ModelRouter
from app.services.gemini_service import GeminiService
from app.modules.languages.practice.services.word_extractor import (
    extract_words_from_translations as extract_words_service,
    filter_segments_by_difficulty as filter_segments_service,
)
from app.modules.languages.media.services.llm_selector import get_available_llm_services
from app.modules.languages.practice.services.phrase_generator import (
    generate_phrase_with_llm as generate_phrase_service,
)
import os
import random
import re
import hashlib
import json

logger = logging.getLogger(__name__)

class PracticeService:
    def __init__(self, db: Session):
        self.db = db

    def check_answer(
        self,
        current_user: User,
        phrase_id: str,
        user_answer: str,
        direction: str = "en-to-pt",
        correct_answer_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica se a resposta do usuário está correta.
        Encapsula a lógica que antes estava no controller practice.py.
        """
        user_answer = user_answer.strip()
        if not user_answer:
            raise HTTPException(status_code=400, detail="Resposta não pode estar vazia")

        # 1. Caso: Palavras avulsas (word-*)
        if phrase_id.startswith('word-'):
            return self._handle_word_check(phrase_id, user_answer, direction, correct_answer_fallback)

        # 2. Caso: Frases geradas (generated-*)
        if phrase_id.startswith('generated-'):
            return self._handle_generated_check(user_answer, correct_answer_fallback)

        # 3. Caso: Segmentos de música (Song ID - Start Time)
        return self._handle_song_segment_check(current_user, phrase_id, user_answer, direction)

    def _handle_word_check(self, phrase_id: str, user_answer: str, direction: str, fallback: Optional[str]) -> Dict[str, Any]:
        correct_answer = fallback
        if not correct_answer:
            word = phrase_id.replace('word-', '')
            correct_answer = self._translate_word_fallback(word, direction)
        
        is_correct = check_answer_similarity(user_answer, correct_answer)
        similarity = calculate_similarity(user_answer, correct_answer)
        
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "similarity": similarity
        }

    def _handle_generated_check(self, user_answer: str, fallback: Optional[str]) -> Dict[str, Any]:
        if not fallback:
            raise HTTPException(status_code=400, detail="Resposta correta não fornecida para frase gerada")
        
        is_correct = check_answer_similarity(user_answer, fallback)
        similarity = calculate_similarity(user_answer, fallback)
        
        return {
            "is_correct": is_correct,
            "correct_answer": fallback,
            "similarity": similarity
        }

    def _handle_song_segment_check(self, current_user: User, phrase_id: str, user_answer: str, direction: str) -> Dict[str, Any]:
        if '-' not in phrase_id:
            raise HTTPException(status_code=400, detail=f"Formato de ID da frase inválido: {phrase_id}")

        try:
            translation_id, segment_start = phrase_id.rsplit('-', 1)
            segment_start_float = float(segment_start)
            translation_uuid = UUID(translation_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail=f"Formato de ID da frase inválido: {phrase_id}")

        translation = self.db.query(Translation).options(
            joinedload(Translation.video)
        ).filter(
            Translation.id == translation_uuid,
            Translation.user_id == current_user.id
        ).first()

        if not translation:
            raise HTTPException(status_code=404, detail="Frase não encontrada")

        correct_answer = self._find_segment_text(translation, segment_start_float, direction)
        
        if not correct_answer:
            raise HTTPException(status_code=404, detail="Segmento não encontrado")

        is_correct = check_answer_similarity(user_answer, correct_answer)
        similarity = calculate_similarity(user_answer, correct_answer)

        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "similarity": similarity
        }

    def _translate_word_fallback(self, word: str, direction: str) -> str:
        """Tenta traduzir usando Gemini ou retorna a própria palavra"""
        try:
            source_lang = "en" if direction == "en-to-pt" else "pt"
            target_lang = "pt" if direction == "en-to-pt" else "en"
            
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                model_router = ModelRouter(validate_on_init=False)
                gemini_service = GeminiService(gemini_key, model_router, validate_models=False)
                return gemini_service._translate_text_with_router(word, target_lang, source_lang)
        except Exception:
            pass
        return word

    def _find_segment_text(self, translation: Translation, start_time: float, direction: str) -> Optional[str]:
        for seg in (translation.segments or []):
            seg_start = seg.get('start', 0)
            if isinstance(seg_start, (int, float)) and abs(seg_start - start_time) < 0.1:
                return seg.get('translated', '') if direction == "en-to-pt" else seg.get('original', '')
        return None

    def get_music_phrase(self, user_id: UUID, direction: str, difficulty: str, video_ids: Optional[List[UUID]] = None) -> Dict[str, Any]:
        """Lógica para obter frase aleatória de músicas traduzidas"""
        query = self.db.query(Translation).join(Video).filter(
            Translation.user_id == user_id,
            Video.user_id == user_id
        )
        
        if video_ids:
            query = query.filter(Video.id.in_(video_ids))
        
        translations = query.options(joinedload(Translation.video)).all()
        if not translations:
            raise HTTPException(status_code=404, detail="Nenhuma tradução encontrada com os critérios especificados")

        candidates = []
        for t in translations:
            if direction == "en-to-pt":
                if t.source_language == "en" and t.target_language == "pt":
                    candidates.append((t, False))
                elif t.source_language == "pt" and t.target_language == "en":
                    candidates.append((t, True))
            elif direction == "pt-to-en":
                if t.source_language == "pt" and t.target_language == "en":
                    candidates.append((t, False))
                elif t.source_language == "en" and t.target_language == "pt":
                    candidates.append((t, True))
            else:
                candidates.append((t, False))

        if not candidates:
            raise HTTPException(status_code=404, detail="Nenhuma tradução encontrada para a direção solicitada")

        translation, inverted = random.choice(candidates)
        video = translation.video  # Já carregado via joinedload

        all_segments = translation.segments or []
        if inverted:
            transformed_segments = []
            for seg in all_segments:
                transformed_segments.append({
                    **seg,
                    'original': seg.get('translated', ''),
                    'translated': seg.get('original', ''),
                })
            use_segments = transformed_segments
            resp_source = 'en' if direction == 'en-to-pt' else 'pt'
            resp_target = 'pt' if direction == 'en-to-pt' else 'en'
        else:
            use_segments = all_segments
            resp_source = translation.source_language
            resp_target = translation.target_language

        filtered_segments = filter_segments_service(use_segments, difficulty) or use_segments
        segment = random.choice(filtered_segments)

        return {
            "id": f"{translation.id}-{segment.get('start', 0)}",
            "original": segment.get('original', ''),
            "translated": segment.get('translated', ''),
            "source_language": resp_source,
            "target_language": resp_target,
            "video_title": video.title if video else None,
            "video_id": str(video.id) if video else None
        }

    def generate_practice_phrase(self, user_id: UUID, direction: str, difficulty: str, video_ids: Optional[List[UUID]] = None, api_keys: Dict[str, str] = None, custom_prompt: str = None, preferred_agent: Dict[str, str] = None) -> Dict[str, Any]:
        """Gera frase nova usando LLM com fallbacks"""
        query = self.db.query(Translation).join(Video).filter(
            Translation.user_id == user_id,
            Video.user_id == user_id
        )
        if video_ids:
            query = query.filter(Video.id.in_(video_ids))
        
        if direction == "en-to-pt":
            query = query.filter(Translation.source_language == "en", Translation.target_language == "pt")
        else:
            query = query.filter(Translation.source_language == "pt", Translation.target_language == "en")
        
        translations = query.all()
        if not translations:
            raise HTTPException(status_code=404, detail="Nenhuma tradução encontrada para gerar frase")
        
        source_words = extract_words_service(translations, direction, difficulty)
        if not source_words:
            raise HTTPException(status_code=404, detail="Não foi possível extrair palavras suficientes")
        
        source_lang = "en" if direction == "en-to-pt" else "pt"
        target_lang = "pt" if direction == "en-to-pt" else "en"
        
        available_services = get_available_llm_services(self.db, user_id, api_keys or {})
        
        if not available_services:
            return self._generate_phrase_fallback(translations, difficulty, direction)

        if preferred_agent:
            available_services = self._reorder_llm_services(available_services, preferred_agent)

        last_error = None
        for service_name, llm_service in available_services:
            try:
                result = generate_phrase_service(llm_service, source_words, source_lang, target_lang, difficulty, custom_prompt=custom_prompt)
                phrase_data = result['phrase']
                used_model = result.get('model', service_name)
                
                phrase_hash = hashlib.md5((phrase_data['original'] + phrase_data['translated']).encode()).hexdigest()[:8]
                return {
                    "id": f"generated-{phrase_hash}",
                    "original": phrase_data['original'],
                    "translated": phrase_data['translated'],
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "model_used": used_model,
                    "service_used": service_name
                }
            except Exception as e:
                last_error = e
                if any(k in str(e).lower() for k in ['quota', 'unavailable', 'rate limit', '429']):
                    continue
                continue

        raise HTTPException(status_code=503, detail=f"Erro ao gerar frase: {str(last_error)}")

    def _generate_phrase_fallback(self, translations: List[Translation], difficulty: str, direction: str) -> Dict[str, Any]:
        translation = random.choice(translations)
        video = self.db.query(Video).filter(Video.id == translation.video_id).first()
        segments = translation.segments or []
        filtered = filter_segments_service(segments, difficulty) or segments
        if not filtered:
            raise HTTPException(status_code=404, detail="Nenhum segmento disponível para fallback")
        segment = random.choice(filtered)
        source_lang = "en" if direction == "en-to-pt" else "pt"
        target_lang = "pt" if direction == "en-to-pt" else "en"
        phrase_hash = hashlib.md5((str(translation.id) + str(segment.get('start', 0))).encode()).hexdigest()[:8]
        return {
            "id": f"generated-fallback-{phrase_hash}",
            "original": segment.get('original', ''),
            "translated": segment.get('translated', ''),
            "source_language": source_lang,
            "target_language": target_lang,
            "video_title": video.title if video else None,
            "video_id": str(video.id) if video else None,
            "model_used": "fallback"
        }

    def _reorder_llm_services(self, services, preferred):
        p_service = preferred.get('service')
        p_model = preferred.get('model')
        reordered = []
        found = False
        for s_name, s_impl in services:
            if s_name == p_service:
                if (s_name == 'gemini' and (getattr(getattr(s_impl, 'gemini_service', None), 'model', None) == p_model or not p_model)) or (getattr(s_impl, 'model_name', None) == p_model or not p_model):
                    reordered.insert(0, (s_name, s_impl))
                    found = True
                    continue
            reordered.append((s_name, s_impl))
        return reordered if found else services

    def get_practice_words(self, user_id: UUID, direction: str, difficulty: str, video_ids: Optional[List[UUID]] = None) -> List[str]:
        query = self.db.query(Translation).join(Video).filter(
            Translation.user_id == user_id,
            Video.user_id == user_id
        )
        if video_ids:
            query = query.filter(Video.id.in_(video_ids))
        
        if direction == "en-to-pt":
            query = query.filter(Translation.source_language == "en", Translation.target_language == "pt")
        else:
            query = query.filter(Translation.source_language == "pt", Translation.target_language == "en")
        
        translations = query.all()
        if not translations:
            raise HTTPException(status_code=404, detail="Nenhuma tradução encontrada")
        
        return extract_words_service(translations, direction, difficulty)

    def get_scramble_phrase(self, user_id: UUID, direction: str, difficulty: str, video_ids: Optional[List[UUID]] = None) -> Dict[str, Any]:
        query = self.db.query(Translation).join(Video).filter(
            Translation.user_id == user_id,
            Video.user_id == user_id
        )
        if video_ids:
            query = query.filter(Video.id.in_(video_ids))
        
        if direction == "en-to-pt":
            query = query.filter(Translation.source_language == "en", Translation.target_language == "pt")
        else:
            query = query.filter(Translation.source_language == "pt", Translation.target_language == "en")

        translations = query.all()
        if not translations:
            raise HTTPException(status_code=404, detail="Nenhuma tradução disponível")

        translation = random.choice(translations)
        video = self.db.query(Video).filter(Video.id == translation.video_id).first()
        segment = random.choice(translation.segments or [])
        
        if direction == "en-to-pt":
            original_text = segment.get('original', '')
            translated_text = segment.get('translated', '')
        else:
            original_text = segment.get('translated', '') or ''
            translated_text = segment.get('original', '') or ''

        tokens = re.findall(r"[A-Za-zÀ-ÿ']+", original_text, flags=re.U)
        shuffled = tokens.copy()
        if len(shuffled) > 1:
            random.shuffle(shuffled)

        return {
            "id": f"{translation.id}-{segment.get('start', 0)}",
            "original": original_text,
            "shuffled": shuffled,
            "translated": translated_text,
            "source_language": translation.source_language,
            "target_language": translation.target_language,
            "video_title": video.title if video else None,
            "video_id": str(video.id) if video else None,
            "start": segment.get('start', 0)
        }

    def check_scramble(self, user_id: UUID, phrase_id: str, sequence: List[str]) -> Dict[str, Any]:
        if '-' not in phrase_id:
            raise HTTPException(status_code=400, detail="Invalid phrase_id format")
        
        translation_id, segment_start = phrase_id.rsplit('-', 1)
        translation = self.db.query(Translation).filter(
            Translation.id == UUID(translation_id),
            Translation.user_id == user_id
        ).first()
        
        if not translation:
            raise HTTPException(status_code=404, detail="Frase não encontrada")

        correct_answer = None
        for seg in (translation.segments or []):
            try:
                if abs(float(seg.get('start', 0)) - float(segment_start)) < 0.1:
                    correct_answer = seg.get('original', '')
                    break
            except Exception:
                continue

        if correct_answer is None:
            raise HTTPException(status_code=404, detail="Segmento não encontrado")

        user_text = ' '.join(sequence)
        ok = check_answer_similarity(user_text, correct_answer)
        return {"is_correct": ok, "correct_answer": correct_answer}

