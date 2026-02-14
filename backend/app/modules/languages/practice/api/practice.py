from fastapi import APIRouter
import logging

"""
Router index for language_learning practice endpoints.
This module only registers subrouters under the /api/practice prefix.
All route implementations live in:
 - agents.py
 - phrases.py
 - words.py
 - answers.py
 - scramble.py
 - cloze.py
"""

router = APIRouter(prefix="/api/practice", tags=["practice"])
logger = logging.getLogger(__name__)

# Legacy submodules imports removed (cloze, agents, phrases, words, answers, scramble)


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database import Video, Translation, User
from app.modules.agents.core_llm.models.models import ApiKey
from app.api.routes.auth import get_current_user
from app.services.encryption import encryption_service
from app.services.gemini_service import GeminiService
from app.modules.agents.core_llm.services.orchestrator.router import ModelRouter
from app.modules.agents.core_llm.services.orchestrator.base import LLMService
from app.modules.agents.core_llm.services.orchestrator.providers import OpenRouterLLMService, GroqLLMService, TogetherAILLMService
from app.modules.agents.core_llm.services.orchestrator.gemini_adapter import GeminiLLMService
from typing import List, Optional
from uuid import UUID
import random
import re
import logging
import os
from app.modules.languages.practice.utils.text_similarity import (
    normalize_text,
    normalize_semantic,
    calculate_similarity,
    check_answer_similarity,
)
from app.modules.languages.practice.constants import EQUIVALENT_WORDS
from app.modules.languages.practice.services.word_extractor import (
    extract_words_from_translations as extract_words_service,
    filter_segments_by_difficulty as filter_segments_service,
)
from app.modules.languages.media.services.llm_selector import get_available_llm_services, get_gemini_service
from app.modules.languages.practice.services.phrase_generator import (
    generate_phrase_with_llm as generate_phrase_service,
    generate_phrase_with_words as generate_phrase_with_words_service,
)
from app.modules.languages.practice.services.practice_service import PracticeService
logger = logging.getLogger(__name__)

#
# Subrouters registered above now contain the actual route implementations.
# This module intentionally keeps only router registration to avoid duplication.
#


@router.post("/phrase/music-context")
async def get_music_phrase(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna uma frase aleatória das músicas traduzidas"""
    try:
        direction = request.get('direction', 'en-to-pt')
        difficulty = request.get('difficulty', 'medium')
        video_ids = request.get('video_ids')
        
        video_ids_list = [UUID(vid) for vid in video_ids] if video_ids else None
        
        service = PracticeService(db)
        return service.get_music_phrase(current_user.id, direction, difficulty, video_ids_list)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar frase de música: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phrase/new-context")
async def generate_practice_phrase(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gera uma frase nova usando LLM com fallback"""
    try:
        direction = request.get('direction', 'en-to-pt')
        difficulty = request.get('difficulty', 'medium')
        video_ids = request.get('video_ids')
        api_keys = request.get('api_keys', {})
        custom_prompt = request.get('custom_prompt')
        preferred_agent = request.get('preferred_agent')
        
        video_ids_list = [UUID(vid) for vid in video_ids] if video_ids else None
        
        service = PracticeService(db)
        return service.generate_practice_phrase(
            current_user.id, direction, difficulty, video_ids_list, api_keys, custom_prompt, preferred_agent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar frase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-answer")
async def check_practice_answer(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica se a resposta do usuário está correta
    """
    try:
        phrase_id = request.get('phrase_id')
        user_answer = request.get('user_answer', '')
        direction = request.get('direction', 'en-to-pt')
        correct_answer_fallback = request.get('correct_answer') # para generated ou word fallback
        
        if not phrase_id:
            raise HTTPException(status_code=400, detail="ID da frase não fornecido")
            
        service = PracticeService(db)
        return service.check_answer(
            current_user=current_user,
            phrase_id=phrase_id,
            user_answer=user_answer,
            direction=direction,
            correct_answer_fallback=correct_answer_fallback
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar resposta: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar resposta: {str(e)}")
 


@router.post("/words")
async def get_practice_words(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna uma lista de palavras extraídas das traduções do usuário"""
    try:
        direction = request.get('direction', 'en-to-pt')
        difficulty = request.get('difficulty', 'medium')
        video_ids = request.get('video_ids')

        video_ids_list = [UUID(vid) for vid in video_ids] if video_ids else None
        
        service = PracticeService(db)
        words = service.get_practice_words(current_user.id, direction, difficulty, video_ids_list)

        return {"words": words}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao extrair palavras")
        raise HTTPException(status_code=500, detail=str(e))


# Listening MC endpoints removed — feature deprecated (only Sentence Scramble kept)


@router.post("/phrase/scramble")
async def get_scramble_phrase(request: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna frase com tokens embaralhados"""
    try:
        direction = request.get('direction', 'en-to-pt')
        difficulty = request.get('difficulty', 'medium')
        video_ids = request.get('video_ids')

        video_ids_list = [UUID(vid) for vid in video_ids] if video_ids else None
        
        service = PracticeService(db)
        return service.get_scramble_phrase(current_user.id, direction, difficulty, video_ids_list)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao gerar scramble")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-scramble")
async def check_scramble(request: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verifica sequência enviada pelo usuário para scramble"""
    try:
        phrase_id = request.get('phrase_id')
        sequence = request.get('sequence', [])
        
        if not phrase_id:
            raise HTTPException(status_code=400, detail="phrase_id required")
            
        service = PracticeService(db)
        return service.check_scramble(current_user.id, phrase_id, sequence)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao verificar scramble")
        raise HTTPException(status_code=500, detail=str(e))


# Word example endpoint removed — Vocabulário cards feature deprecated

def generate_phrase_with_words(
    gemini_service: GeminiLLMService,
    words: List[str],
    source_lang: str,
    target_lang: str,
    difficulty: str
) -> dict:
    """Gera frase usando GeminiService (mantido para compatibilidade)"""
    llm_service = GeminiLLMService(gemini_service)
    return generate_phrase_service(llm_service, words, source_lang, target_lang, difficulty)


 
