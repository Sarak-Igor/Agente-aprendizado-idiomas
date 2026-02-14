"""
Roteador Inteligente para Modelos Gemini
Gerencia disponibilidade, cotas e seleção de modelos
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

class ModelRouter:
    """Roteador para gerenciar múltiplos modelos Gemini com fallback e controle de cota"""
    
    AVAILABLE_MODELS = settings.gemini_models
    
    def __init__(self, validate_on_init: bool = False, gemini_client = None):
        self.blocked_models: Dict[str, datetime] = {}
        self.validated_models: Dict[str, bool] = {}
        self.last_validation: Optional[datetime] = None
        self.revalidate_interval = timedelta(hours=1)
        
        if validate_on_init and gemini_client:
            self.validate_available_models(gemini_client)

    def get_next_model(self, exclude_models: Optional[List[str]] = None) -> Optional[str]:
        """Retorna o próximo modelo disponível"""
        exclude = set(exclude_models or [])
        now = datetime.now()
        
        # Remove modelos cujo bloqueio expirou (10 min)
        self.blocked_models = {m: t for m, t in self.blocked_models.items() if now < t + timedelta(minutes=10)}
        
        for model in self.AVAILABLE_MODELS:
            if model not in exclude and model not in self.blocked_models:
                return model
        return None

    def record_success(self, model_name: str):
        self.validated_models[model_name] = True
        if model_name in self.blocked_models:
            del self.blocked_models[model_name]

    def record_error(self, model_name: str, error_type: str):
        if error_type in ['quota', 'not_found', 'api_error']:
            self.blocked_models[model_name] = datetime.now()
            self.validated_models[model_name] = False

    def validate_available_models(self, client):
        """Valida quais modelos estão realmente disponíveis na conta"""
        logger.info("Validando modelos Gemini...")
        for model in self.AVAILABLE_MODELS:
            try:
                # Teste leve: apenas tenta listar o modelo ou similar
                client.models.get(model=model)
                self.validated_models[model] = True
            except Exception:
                self.validated_models[model] = False
        self.last_validation = datetime.now()

    def get_validated_models(self) -> List[str]:
        return [m for m, v in self.validated_models.items() if v]

    def get_blocked_models_list(self) -> List[str]:
        return list(self.blocked_models.keys())

    def should_revalidate(self) -> bool:
        if not self.last_validation: return True
        return datetime.now() > self.last_validation + self.revalidate_interval

    def get_model_category(self, model_name: str) -> str:
        if 'flash' in model_name: return 'fast'
        if 'pro' in model_name: return 'high_intelligence'
        return 'general'
