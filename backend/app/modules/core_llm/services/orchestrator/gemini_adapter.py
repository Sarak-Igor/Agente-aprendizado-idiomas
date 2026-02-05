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
    
    def __init__(self, google_client, model_router, token_usage_service=None, db=None):
        self.client = google_client
        self.model_router = model_router
        self.token_usage_service = token_usage_service
        self.db = db
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        """Gera texto usando roteamento inteligente entre modelos Gemini"""
        
        # Se um modelo específico foi solicitado, tenta usar
        if model_name:
            tried_models = [model_name]
            candidates = [model_name]
        else:
            # Tenta usar Universal Selector se DB disponível
            candidates = []
            if self.db:
                try:
                    from app.modules.core_llm.services.selector import UniversalModelSelector, SelectionRequest, ModelCapability
                    selector = UniversalModelSelector(self.db)
                    req = SelectionRequest(
                        user_id="system", 
                        function_name="chat",
                        required_capabilities=[ModelCapability.TEXT_INPUT]
                    )
                    result = selector.select_model(req)
                    # Adiciona o selecionado e alternativas
                    candidates.append(result.selected_model.model)
                    candidates.extend([m.model for m in result.alternatives])
                except Exception as e:
                    logger.warning(f"Falha ao usar UniversalModelSelector no GeminiAdapter: {e}")
            
            # Fallback para Legacy Router se Selector falhou ou sem DB
            if not candidates:
                candidates = [self.model_router.get_next_model()]

        tried_models = []
        max_attempts = 3
        
        # Itera sobre candidatos (com retries no legado, ou lista de alternativas no novo)
        # Se candidates veio do Selector, usamo-los em ordem.
        # Se veio do legacy, é um só por vez, precisamos loopar chamando get_next.
        
        using_legacy = (not self.db) and (not model_name)
        
        for attempt in range(max_attempts):
            if using_legacy and attempt > 0:
                current_model = self.model_router.get_next_model(exclude_models=tried_models)
            else:
                current_model = candidates[attempt] if attempt < len(candidates) else None
            
            if not current_model:
                break
                
            tried_models.append(current_model)
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config={"max_output_tokens": max_tokens or 2048}
                )
                
                result = response.text.strip()
                if result:
                    self.model_router.record_success(current_model)
                    if self.token_usage_service:
                        usage = getattr(response, 'usage_metadata', None)
                        if usage:
                            self.token_usage_service.record_usage(
                                service='gemini', model=current_model,
                                input_tokens=getattr(usage, 'prompt_token_count', 0),
                                output_tokens=getattr(usage, 'candidates_token_count', 0)
                            )
                    return result
            except Exception as e:
                logger.warning(f"Erro no modelo Gemini {current_model}: {e}")
                last_exception = e
                self.model_router.record_error(current_model, str(e))
                
        raise Exception(f"Erro nos modelos Gemini: {str(last_exception) if last_exception else 'Nenhum modelo disponível'}")
