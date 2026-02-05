"""
Interfaces base para serviços LLM
"""
from abc import ABC, abstractmethod
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Erro base para serviços LLM"""
    def __init__(self, message: str, service: str = None, model: str = None):
        self.message = message
        self.service = service
        self.model = model
        super().__init__(self.message)

class InsufficientBalanceError(LLMError):
    """Erro 402 - Saldo insuficiente no provedor"""
    pass

class QuotaExceededError(LLMError):
    """Erro 429 - Limite de taxa ou cota atingido"""
    pass

class LLMService(ABC):
    """Interface base para serviços LLM"""
    
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Gera texto usando o LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        pass

class CompositeLLMService(LLMService):
    """Serviço que tenta múltiplos provedores em sequência (Fallback)"""
    
    def __init__(self, services: List[LLMService]):
        self.services = [s for s in services if s is not None]
    
    def is_available(self) -> bool:
        return any(s.is_available() for s in self.services)
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        last_error = None
        for service in self.services:
            if not service.is_available():
                continue
            try:
                return service.generate_text(prompt, max_tokens)
            except Exception as e:
                logger.warning(f"Falha no provedor {service.__class__.__name__}: {e}")
                last_error = e
                continue
        
        raise Exception(f"Todos os provedores LLM falharam. Último erro: {last_error}")
