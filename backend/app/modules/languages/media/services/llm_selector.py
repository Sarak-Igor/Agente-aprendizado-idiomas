import os
import logging
from typing import List, Optional
from uuid import UUID

from app.services.encryption import encryption_service
from app.modules.agents.core_llm.models.models import ApiKey
from app.modules.agents.core_llm.services.orchestrator.router import ModelRouter
from app.modules.agents.core_llm.services.orchestrator.base import LLMService
from app.modules.agents.core_llm.services.orchestrator.providers import OpenRouterLLMService, GroqLLMService, TogetherAILLMService
from app.modules.agents.core_llm.services.orchestrator.gemini_adapter import GeminiLLMService

logger = logging.getLogger(__name__)


def get_gemini_service(user_id: UUID, db, validate_models: bool = True):
    try:
        api_key_record = db.query(ApiKey).filter(
            ApiKey.user_id == user_id,
            ApiKey.service == "gemini"
        ).first()

        if not api_key_record:
            return None

        decrypted_key = encryption_service.decrypt(api_key_record.encrypted_key)
        model_router = ModelRouter(validate_on_init=False)
        return GeminiLLMService(decrypted_key, model_router, validate_models=validate_models, db=db)
    except Exception as e:
        logger.error(f"Erro ao obter GeminiService: {e}")
        return None


def get_available_llm_services(db, user_id: UUID, api_keys_from_request: Optional[dict] = None) -> List[tuple]:
    from app.modules.agents.core_llm.services.usage.token_usage_service import TokenUsageService

    services = []
    api_keys = api_keys_from_request or {}
    token_usage_service = TokenUsageService(db)

    gemini_service = get_gemini_service(user_id, db, validate_models=False)
    if gemini_service:
        try:
            gemini_llm = GeminiLLMService(gemini_service)
            if gemini_llm.is_available():
                services.append(('gemini', gemini_llm))
                logger.info("Gemini disponível para geração de frases")
        except Exception as e:
            logger.debug(f"Gemini não disponível: {e}")

    # OpenRouter
    try:
        openrouter_key = api_keys.get('openrouter')
        if not openrouter_key:
            api_key_record = db.query(ApiKey).filter(
                ApiKey.user_id == user_id,
                ApiKey.service == "openrouter"
            ).first()
            if api_key_record:
                openrouter_key = encryption_service.decrypt(api_key_record.encrypted_key)
        if not openrouter_key:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            openrouter_service = OpenRouterLLMService(openrouter_key, token_usage_service)
            if openrouter_service.is_available():
                services.append(('openrouter', openrouter_service))
                logger.info("OpenRouter disponível para geração de frases")
    except Exception as e:
        logger.debug(f"OpenRouter não disponível: {e}")

    # Groq
    try:
        groq_key = api_keys.get('groq')
        if not groq_key:
            api_key_record = db.query(ApiKey).filter(
                ApiKey.user_id == user_id,
                ApiKey.service == "groq"
            ).first()
            if api_key_record:
                groq_key = encryption_service.decrypt(api_key_record.encrypted_key)
        if not groq_key:
            groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            groq_service = GroqLLMService(groq_key, token_usage_service)
            if groq_service.is_available():
                services.append(('groq', groq_service))
                logger.info("Groq disponível para geração de frases")
    except Exception as e:
        logger.debug(f"Groq não disponível: {e}")

    # Together AI
    try:
        together_key = api_keys.get('together')
        if not together_key:
            api_key_record = db.query(ApiKey).filter(
                ApiKey.user_id == user_id,
                ApiKey.service == "together"
            ).first()
            if api_key_record:
                together_key = encryption_service.decrypt(api_key_record.encrypted_key)
        if not together_key:
            together_key = os.getenv("TOGETHER_API_KEY")
        if together_key:
            together_service = TogetherAILLMService(together_key, token_usage_service)
            if together_service.is_available():
                services.append(('together', together_service))
                logger.info("Together AI disponível para geração de frases")
    except Exception as e:
        logger.debug(f"Together AI não disponível: {e}")

    return services

