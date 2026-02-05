"""
Implementações de provedores LLM (OpenRouter, Groq, Together)
"""
import logging
import httpx
from typing import Optional
from app.modules.core_llm.services.orchestrator.base import (
    LLMService, 
    InsufficientBalanceError, 
    QuotaExceededError, 
    LLMError
)

logger = logging.getLogger(__name__)

class OpenRouterLLMService(LLMService):
    """Serviço LLM usando OpenRouter"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "openai/gpt-3.5-turbo"
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        model_to_use = model_name or self.model_name
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model_to_use,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens or 500
                    }
                )
                if response.status_code == 200:
                    # ... (mantém lógica de sucesso) ...
                    data = response.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    if self.token_usage_service:
                        usage = data.get("usage", {})
                        self.token_usage_service.record_usage(
                            service='openrouter', model=model_to_use,
                            input_tokens=usage.get("prompt_tokens", 0),
                            output_tokens=usage.get("completion_tokens", 0)
                        )
                    return result
                
                if response.status_code == 402:
                    raise InsufficientBalanceError("Saldo insuficiente no OpenRouter", service="openrouter", model=model_to_use)
                if response.status_code == 429:
                    raise QuotaExceededError("Limite de cota atingido no OpenRouter", service="openrouter", model=model_to_use)
                    
                raise LLMError(f"Erro OpenRouter: {response.status_code}", service="openrouter", model=model_to_use)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado OpenRouter: {e}")
            raise LLMError(f"Erro inesperado: {str(e)}", service="openrouter", model=model_to_use)

class GroqLLMService(LLMService):
    """Serviço LLM usando Groq"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "llama-3.1-8b-instant"
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        model_to_use = model_name or self.model_name
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model_to_use,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens or 500
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    if self.token_usage_service:
                        usage = data.get("usage", {})
                        self.token_usage_service.record_usage(
                            service='groq', model=model_to_use,
                            input_tokens=usage.get("prompt_tokens", 0),
                            output_tokens=usage.get("completion_tokens", 0)
                        )
                    return result

                if response.status_code == 402:
                    raise InsufficientBalanceError("Saldo insuficiente no Groq/OpenAI", service="groq", model=model_to_use)
                if response.status_code == 429:
                    raise QuotaExceededError("Cota atingida no Groq", service="groq", model=model_to_use)
                
                raise LLMError(f"Erro Groq: {response.status_code}", service="groq", model=model_to_use)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado Groq: {e}")
            raise LLMError(f"Erro inesperado: {str(e)}", service="groq", model=model_to_use)

class TogetherAILLMService(LLMService):
    """Serviço LLM usando Together AI"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://api.together.xyz/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "meta-llama/Llama-3-8b-chat-hf"
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        model_to_use = model_name or self.model_name
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model_to_use,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens or 500
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    if self.token_usage_service:
                        usage = data.get("usage", {})
                        self.token_usage_service.record_usage(
                            service='together', model=model_to_use,
                            input_tokens=usage.get("prompt_tokens", 0),
                            output_tokens=usage.get("completion_tokens", 0)
                        )
                    return result
                
                if response.status_code == 402:
                    raise InsufficientBalanceError("Saldo insuficiente no Together AI", service="together", model=model_to_use)
                if response.status_code == 429:
                    raise QuotaExceededError("Cota atingida no Together AI", service="together", model=model_to_use)
                
                raise LLMError(f"Erro Together AI: {response.status_code}", service="together", model=model_to_use)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado Together: {e}")
            raise LLMError(f"Erro inesperado: {str(e)}", service="together", model=model_to_use)
