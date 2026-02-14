import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.modules.agents.core_llm.models.models import ApiKey
from app.services.encryption import encryption_service
from app.modules.agents.core_llm.services.orchestrator.providers import OpenRouterLLMService, GroqLLMService
from app.modules.agents.core_llm.services.orchestrator.gemini_adapter import GeminiLLMService
from app.modules.agents.core_llm.services.orchestrator.router import ModelRouter
from google import genai

logger = logging.getLogger(__name__)

class LLMProvider:
    """
    Utilitário para instanciar provedores LLM do core_llm usando as chaves do usuário.
    """
    
    @staticmethod
    def get_service(db: Session, user_id, service_name: str):
        """
        Retorna uma instância de LLMService inicializada com a chave do usuário.
        """
        from sqlalchemy import func
        api_key_record = db.query(ApiKey).filter(
            ApiKey.user_id == user_id,
            func.lower(ApiKey.service) == func.lower(service_name)
        ).first()
        
        if not api_key_record:
            logger.warning(f"Chave de API não encontrada para o serviço {service_name} e usuário {user_id}")
            return None
            
        try:
            api_key = encryption_service.decrypt(api_key_record.encrypted_key)
            
            if service_name == "openrouter":
                return OpenRouterLLMService(api_key=api_key)
            elif service_name == "groq":
                return GroqLLMService(api_key=api_key)
            elif service_name == "gemini":
                # Gemini requer client e router
                client = genai.Client(api_key=api_key)
                model_router = ModelRouter(validate_on_init=False)
                return GeminiLLMService(google_client=client, model_router=model_router, db=db)
                
            return None
        except Exception as e:
            logger.error(f"Erro ao inicializar serviço {service_name}: {e}")
            return None
