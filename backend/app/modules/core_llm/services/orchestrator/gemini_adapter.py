"""
Adaptador para o serviço Gemini, integrado ao ModelRouter
"""
import logging
from datetime import datetime
from typing import Optional, List
from app.modules.core_llm.services.orchestrator.base import LLMService

logger = logging.getLogger(__name__)

class GeminiLLMService(LLMService):
    """Adaptador para o Google Gemini com suporte a Fallback e Roteamento"""
    
    def __init__(self, google_client, model_router, token_usage_service=None):
        self.client = google_client
        self.model_router = model_router
        self.token_usage_service = token_usage_service
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Gera texto usando roteamento inteligente entre modelos Gemini"""
        tried_models = []
        max_attempts = 3
        
        for attempt in range(max_attempts):
            model_name = self.model_router.get_next_model(exclude_models=tried_models)
            if not model_name:
                break
                
            tried_models.append(model_name)
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"max_output_tokens": max_tokens or 2048}
                )
                
                result = response.text.strip()
                if result:
                    self.model_router.record_success(model_name)
                    if self.token_usage_service:
                        usage = getattr(response, 'usage_metadata', None)
                        if usage:
                            self.token_usage_service.record_usage(
                                service='gemini', model=model_name,
                                input_tokens=getattr(usage, 'prompt_token_count', 0),
                                output_tokens=getattr(usage, 'candidates_token_count', 0)
                            )
                    return result
            except Exception as e:
                logger.warning(f"Erro no modelo Gemini {model_name}: {e}")
                self.model_router.record_error(model_name, str(e))
                
        raise Exception(f"Falha em todos os modelos Gemini tentados: {tried_models}")
