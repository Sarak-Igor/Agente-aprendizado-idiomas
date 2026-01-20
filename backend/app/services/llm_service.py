"""
Serviço base para LLMs (Large Language Models)
Interface comum para diferentes provedores
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LLMService(ABC):
    """Interface base para serviços LLM"""
    
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Gera texto usando o LLM
        
        Args:
            prompt: Prompt para o modelo
            max_tokens: Número máximo de tokens (opcional)
            
        Returns:
            Texto gerado pelo modelo
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        pass


class OpenRouterLLMService(LLMService):
    """Serviço LLM usando OpenRouter"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "openai/gpt-3.5-turbo"  # Modelo padrão
    
    def is_available(self) -> bool:
        """Verifica se a chave está configurada"""
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        """Gera texto usando OpenRouter"""
        import httpx
        
        # Usa modelo fornecido ou padrão
        model_to_use = model_name or self.model_name
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://github.com",
                        "X-Title": "Translation System",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_to_use,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens or 500
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        result = data["choices"][0]["message"]["content"].strip()
                        
                        # Captura informações de uso de tokens
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0
                        
                        if "usage" in data:
                            usage = data["usage"]
                            input_tokens = usage.get("prompt_tokens", 0)
                            output_tokens = usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0)
                        
                        # Registra uso de tokens se o serviço estiver disponível
                        if self.token_usage_service and (input_tokens > 0 or output_tokens > 0 or total_tokens > 0):
                            try:
                                self.token_usage_service.record_usage(
                                    service='openrouter',
                                    model=model_to_use,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=total_tokens if total_tokens > 0 else None,
                                    requests=1,
                                    user_id=None
                                )
                            except Exception as e:
                                logger.debug(f"Erro ao registrar tokens do OpenRouter: {e}")
                        
                        return result
                    else:
                        raise Exception("Resposta vazia do OpenRouter")
                elif response.status_code == 401:
                    raise Exception("Chave de API OpenRouter inválida")
                elif response.status_code == 402:
                    raise Exception("Sem créditos suficientes no OpenRouter")
                else:
                    raise Exception(f"Erro do OpenRouter: Status {response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Timeout ao conectar com OpenRouter")
        except Exception as e:
            logger.error(f"Erro ao gerar texto com OpenRouter: {e}")
            raise


class GroqLLMService(LLMService):
    """Serviço LLM usando Groq"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "llama-3.1-8b-instant"  # Modelo padrão
    
    def is_available(self) -> bool:
        """Verifica se a chave está configurada"""
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        """Gera texto usando Groq"""
        import httpx
        
        # Usa modelo fornecido ou padrão
        model_to_use = model_name or self.model_name
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_to_use,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens or 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        result = data["choices"][0]["message"]["content"].strip()
                        
                        # Captura informações de uso de tokens
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0
                        
                        if "usage" in data:
                            usage = data["usage"]
                            input_tokens = usage.get("prompt_tokens", 0)
                            output_tokens = usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0)
                        
                        # Registra uso de tokens se o serviço estiver disponível
                        if self.token_usage_service and (input_tokens > 0 or output_tokens > 0 or total_tokens > 0):
                            try:
                                self.token_usage_service.record_usage(
                                    service='groq',
                                    model=model_to_use,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=total_tokens if total_tokens > 0 else None,
                                    requests=1,
                                    user_id=None
                                )
                            except Exception as e:
                                logger.debug(f"Erro ao registrar tokens do Groq: {e}")
                        
                        return result
                    else:
                        raise Exception("Resposta vazia do Groq")
                elif response.status_code == 401:
                    raise Exception("Chave de API Groq inválida")
                else:
                    raise Exception(f"Erro do Groq: Status {response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Timeout ao conectar com Groq")
        except Exception as e:
            logger.error(f"Erro ao gerar texto com Groq: {e}")
            raise


class TogetherAILLMService(LLMService):
    """Serviço LLM usando Together AI"""
    
    def __init__(self, api_key: str, token_usage_service=None):
        self.api_key = api_key
        self.base_url = "https://api.together.xyz/v1"
        self.token_usage_service = token_usage_service
        self.model_name = "meta-llama/Llama-3-8b-chat-hf"  # Modelo padrão
    
    def is_available(self) -> bool:
        """Verifica se a chave está configurada"""
        return bool(self.api_key and self.api_key.strip())
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, model_name: Optional[str] = None) -> str:
        """Gera texto usando Together AI"""
        import httpx
        
        # Usa modelo fornecido ou padrão
        model_to_use = model_name or self.model_name
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_to_use,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens or 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        result = data["choices"][0]["message"]["content"].strip()
                        
                        # Captura informações de uso de tokens
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0
                        
                        if "usage" in data:
                            usage = data["usage"]
                            input_tokens = usage.get("prompt_tokens", 0)
                            output_tokens = usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0)
                        
                        # Registra uso de tokens se o serviço estiver disponível
                        if self.token_usage_service and (input_tokens > 0 or output_tokens > 0 or total_tokens > 0):
                            try:
                                self.token_usage_service.record_usage(
                                    service='together',
                                    model=model_to_use,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=total_tokens if total_tokens > 0 else None,
                                    requests=1,
                                    user_id=None
                                )
                            except Exception as e:
                                logger.debug(f"Erro ao registrar tokens do Together AI: {e}")
                        
                        return result
                    else:
                        raise Exception("Resposta vazia do Together AI")
                elif response.status_code == 401:
                    raise Exception("Chave de API Together AI inválida")
                else:
                    raise Exception(f"Erro do Together AI: Status {response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Timeout ao conectar com Together AI")
        except Exception as e:
            logger.error(f"Erro ao gerar texto com Together AI: {e}")
            raise


class GeminiLLMService(LLMService):
    """Adapter para usar GeminiService como LLMService"""
    
    def __init__(self, gemini_service):
        self.gemini_service = gemini_service
    
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return self.gemini_service is not None
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Gera texto usando Gemini diretamente"""
        try:
            # Usa o cliente Gemini diretamente para enviar o prompt
            # Sem wrapper de tradução, apenas geração de texto
            # Tenta TODOS os modelos disponíveis antes de falhar
            
            # Filtra modelos inadequados para geração de texto
            def is_text_generation_model(model_name: str) -> bool:
                """Verifica se o modelo é adequado para geração de texto"""
                model_lower = model_name.lower()
                # Exclui modelos de embedding, veo (vídeo), computer-use, robotics, etc.
                excluded_keywords = [
                    'embedding', 'veo', 'computer-use', 'robotics', 
                    'native-audio', 'tts', 'vision', 'image-generation',
                    'exp-', 'preview-', 'lite-preview'
                ]
                return not any(keyword in model_lower for keyword in excluded_keywords)
            
            # Calcula número de tentativas baseado em modelos disponíveis
            all_available = self.gemini_service.model_router.get_available_models()
            text_models = [m for m in all_available if is_text_generation_model(m)]
            max_attempts = min(len(text_models) * 2, 50)  # Tenta até 2x o número de modelos, máximo 50
            if max_attempts < 10:
                max_attempts = 10  # Mínimo de 10 tentativas
            
            tried_models = []
            last_error = None
            
            for attempt in range(max_attempts):
                # Revalida modelos se necessário
                if self.gemini_service.model_router.should_revalidate():
                    try:
                        logger.info("Revalidando modelos disponíveis...")
                        self.gemini_service.model_router.validate_available_models(self.gemini_service.client)
                    except Exception as e:
                        logger.debug(f"Erro ao revalidar modelos: {e}")
                
                # Obtém próximo modelo disponível (excluindo os já tentados e bloqueados)
                # Limpa bloqueios temporários expirados primeiro
                now = datetime.now()
                expired_blocks = [
                    model for model, block_info in self.gemini_service.model_router.temporary_blocks.items()
                    if block_info.get('blocked_until') and now >= block_info['blocked_until']
                ]
                for model in expired_blocks:
                    if model in self.gemini_service.model_router.temporary_blocks:
                        del self.gemini_service.model_router.temporary_blocks[model]
                        logger.info(f"Bloqueio temporário do modelo {model} expirou")
                
                validated_models = self.gemini_service.model_router.get_validated_models()
                exclude = set(tried_models)
                exclude.update(self.gemini_service.model_router.blocked_models)
                # Adiciona modelos bloqueados temporariamente
                for model, block_info in self.gemini_service.model_router.temporary_blocks.items():
                    blocked_until = block_info.get('blocked_until')
                    if blocked_until and now < blocked_until:
                        exclude.add(model)
                
                # Tenta primeiro modelos validados (filtrados)
                available_validated = [m for m in validated_models if m not in exclude and is_text_generation_model(m)]
                if available_validated:
                    model_name = available_validated[0]
                else:
                    # Se não há modelos validados, tenta qualquer modelo disponível (filtrado)
                    all_models = self.gemini_service.model_router.get_available_models()
                    text_models = [m for m in all_models if m not in exclude and is_text_generation_model(m)]
                    if text_models:
                        model_name = text_models[0]
                    else:
                        model_name = None
                
                # Se não há mais modelos para tentar, tenta listar modelos dinamicamente da API
                if not model_name:
                    logger.info("Nenhum modelo disponível na lista fixa. Tentando listar modelos dinamicamente da API...")
                    try:
                        # Tenta carregar modelos dinamicamente da API
                        dynamic_models = self.gemini_service.model_router._load_available_models(
                            self.gemini_service.client
                        )
                        if dynamic_models:
                            # Filtra modelos já tentados, bloqueados e inadequados
                            new_models = [m for m in dynamic_models if m not in exclude and is_text_generation_model(m)]
                            if new_models:
                                model_name = new_models[0]
                                logger.info(f"Modelo encontrado dinamicamente: {model_name}")
                            else:
                                logger.warning("Nenhum modelo novo adequado encontrado na listagem dinâmica")
                    except Exception as e:
                        logger.debug(f"Erro ao listar modelos dinamicamente: {e}")
                    
                    # Se ainda não há modelo, tenta modelos não validados (filtrados)
                    if not model_name:
                        all_models = self.gemini_service.model_router.get_available_models()
                        untried_models = [m for m in all_models if m not in exclude and is_text_generation_model(m)]
                        if untried_models:
                            model_name = untried_models[0]
                            logger.info(f"Tentando modelo não validado: {model_name}")
                
                if not model_name:
                    # Última tentativa: limpa bloqueios temporários expirados e tenta novamente
                    logger.info("Limpa bloqueios temporários expirados e tenta novamente...")
                    all_models = self.gemini_service.model_router.get_available_models()
                    untried_models = [m for m in all_models if m not in exclude]
                    if untried_models:
                        model_name = untried_models[0]
                        logger.info(f"Modelo disponível após limpeza de bloqueios: {model_name}")
                
                if not model_name:
                    blocked = self.gemini_service.model_router.get_blocked_models_list()
                    validated = self.gemini_service.model_router.get_validated_models()
                    available = self.gemini_service.model_router.get_available_models()
                    raise Exception(
                        f"Todos os modelos Gemini foram tentados e estão indisponíveis. "
                        f"Modelos bloqueados permanentemente: {blocked}. "
                        f"Modelos validados: {validated}. "
                        f"Modelos disponíveis: {available}. "
                        f"Tentativas: {len(tried_models)}. "
                        f"Verifique suas cotas de API ou configure outros serviços LLM como fallback."
                    )
                
                tried_models.append(model_name)
                logger.debug(f"Tentativa {attempt + 1}/{max_attempts}: usando modelo {model_name}")
                
                try:
                    response = self.gemini_service.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    
                    # Extrai texto da resposta
                    result = None
                    if hasattr(response, 'text'):
                        result = response.text.strip()
                    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content'):
                            if hasattr(candidate.content, 'parts') and len(candidate.content.parts) > 0:
                                result = candidate.content.parts[0].text.strip()
                            elif hasattr(candidate.content, 'text'):
                                result = candidate.content.text.strip()
                    
                    if result:
                        # Registra sucesso
                        self.gemini_service.model_router.record_success(model_name)
                        
                        # Captura tokens (se disponível)
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0
                        
                        try:
                            if hasattr(response, 'usage_metadata'):
                                usage = response.usage_metadata
                                if hasattr(usage, 'prompt_token_count'):
                                    input_tokens = usage.prompt_token_count
                                if hasattr(usage, 'candidates_token_count'):
                                    output_tokens = usage.candidates_token_count
                                if hasattr(usage, 'total_token_count'):
                                    total_tokens = usage.total_token_count
                        except:
                            pass
                        
                        # Registra uso de tokens (user_id é opcional)
                        if self.gemini_service.token_usage_service and (input_tokens > 0 or output_tokens > 0 or total_tokens > 0):
                            try:
                                self.gemini_service.token_usage_service.record_usage(
                                    service='gemini',
                                    model=model_name,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=total_tokens if total_tokens > 0 else None,
                                    requests=1,
                                    user_id=None  # user_id não disponível neste contexto
                                )
                            except Exception as e:
                                logger.debug(f"Erro ao registrar tokens (não crítico): {e}")
                        
                        # Remove aspas se presentes
                        result = result.strip('"').strip("'").strip()
                        return result
                        
                except Exception as e:
                    error_str = str(e)
                    error_repr = repr(e)
                    
                    last_error = e
                    
                    # Se for erro 404 (modelo não encontrado), bloqueia temporariamente e tenta próximo
                    if '404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower() or '404' in error_repr:
                        logger.warning(f"Modelo {model_name} não encontrado (404). Bloqueando temporariamente e tentando próximo modelo...")
                        self.gemini_service.model_router.record_error(model_name, 'not_found')
                        self.gemini_service.model_router.block_model(model_name, 'not_found', permanent=False)
                        self.gemini_service.model_router.validated_models[model_name] = False
                        logger.info(f"Tentando próximo modelo (tentativa {attempt + 1}/{max_attempts})...")
                        continue
                    
                    # Se for erro 429 ou RESOURCE_EXHAUSTED
                    is_quota_error = (
                        '429' in error_str or 
                        'RESOURCE_EXHAUSTED' in error_str or 
                        '429' in error_repr or
                        'RESOURCE_EXHAUSTED' in error_repr
                    )
                    
                    if is_quota_error:
                        # Verifica se é realmente cota excedida ou modelo não disponível
                        # Se a mensagem menciona "limit: 0", pode ser que o modelo não esteja disponível para a conta
                        is_model_unavailable = 'limit: 0' in error_str or 'limit:0' in error_str
                        
                        if is_model_unavailable:
                            logger.warning(f"Modelo {model_name} não disponível para esta conta (limite 0). Bloqueando temporariamente e tentando próximo modelo...")
                            self.gemini_service.model_router.record_error(model_name, 'not_available')
                            # Bloqueio temporário - pode ser apenas restrição de API version
                            self.gemini_service.model_router.block_model(model_name, 'not_available', permanent=False)
                        else:
                            logger.warning(f"Modelo {model_name} sem cota disponível (429). Bloqueando temporariamente e tentando próximo modelo...")
                            self.gemini_service.model_router.record_error(model_name, 'quota')
                            # Bloqueio temporário - cota pode resetar
                            self.gemini_service.model_router.block_model(model_name, 'quota_exceeded', permanent=False)
                        
                        self.gemini_service.model_router.validated_models[model_name] = False
                        
                        # Sempre tenta próximo modelo se houver mais tentativas
                        logger.info(f"Tentando próximo modelo disponível (tentativa {attempt + 1}/{max_attempts})...")
                        continue
                    
                    # Para outros erros, bloqueia temporariamente e tenta próximo modelo
                    logger.warning(f"Erro ao usar modelo {model_name}: {error_str[:200]}. Bloqueando temporariamente e tentando próximo modelo...")
                    self.gemini_service.model_router.record_error(model_name, 'api_error')
                    # Bloqueio temporário - pode ser erro temporário
                    self.gemini_service.model_router.block_model(model_name, 'api_error', permanent=False)
                    continue
            
            # Se chegou aqui, tentou todos os modelos e nenhum funcionou
            blocked = self.gemini_service.model_router.get_blocked_models_list()
            available = self.gemini_service.model_router.get_available_models()
            raise Exception(
                f"Nenhum modelo Gemini disponível após {len(tried_models)} tentativas. "
                f"Modelos tentados: {tried_models}. "
                f"Modelos bloqueados: {blocked}. "
                f"Modelos disponíveis: {available}. "
                f"Último erro: {str(last_error)[:200] if last_error else 'desconhecido'}. "
                f"Configure outros serviços LLM (OpenRouter, Groq, Together) como fallback."
            )
            
        except Exception as e:
            logger.error(f"Erro ao gerar texto com Gemini: {e}")
            raise
