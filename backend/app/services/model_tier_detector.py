"""
Serviço para detectar tier (free/paid) de modelos LLM através de testes reais
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pydantic import BaseModel
import logging
import asyncio

from app.services.model_test_utils import (
    create_minimal_image_base64,
    create_minimal_audio_base64,
    analyze_response_headers
)
from app.services.model_router import ModelRouter

logger = logging.getLogger(__name__)

# TTL do cache: 3 horas
CACHE_TTL_SECONDS = 3 * 60 * 60  # 10800 segundos


@dataclass
class ModelTierInfo:
    """Informações sobre tier de um modelo"""
    model_name: str
    service: str
    category: str
    tier: str  # "free", "paid", "unknown"
    detection_method: str  # "test_request", "metadata", "usage_based", "pricing_endpoint"
    confidence: float  # 0.0 a 1.0
    available: bool
    quota_info: Optional[Dict[str, Any]] = None  # Para free tier
    cost_info: Optional[Dict[str, Any]] = None  # Para paid tier
    last_checked: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        result = asdict(self)
        if self.last_checked:
            result['last_checked'] = self.last_checked.isoformat()
        return result


class ModelTierDetector:
    """
    Detecta tier (free/paid) de modelos LLM através de testes reais
    """
    
    def __init__(self):
        # Cache em memória: {user_id: {last_updated: datetime, models: {model_name: ModelTierInfo}}}
        self._tier_cache: Dict[str, Dict] = {}
    
    def get_cached_tiers(self, user_id: str) -> Optional[Dict[str, ModelTierInfo]]:
        """
        Obtém tiers em cache para um usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dicionário {model_name: ModelTierInfo} ou None se cache expirado/inexistente
        """
        cache_key = f"user:{user_id}"
        
        if cache_key not in self._tier_cache:
            return None
        
        cache_data = self._tier_cache[cache_key]
        last_updated = cache_data.get('last_updated')
        
        if not last_updated:
            return None
        
        # Verifica se cache expirou (3 horas)
        age = datetime.now() - last_updated
        if age.total_seconds() > CACHE_TTL_SECONDS:
            # Remove cache expirado
            del self._tier_cache[cache_key]
            return None
        
        # Retorna modelos do cache
        return cache_data.get('models', {})
    
    def cache_tiers(self, user_id: str, tiers: Dict[str, ModelTierInfo], merge: bool = True):
        """
        Salva tiers no cache, mesclando com existentes se merge=True
        
        Args:
            user_id: ID do usuário
            tiers: Dicionário {model_name: ModelTierInfo}
            merge: Se True, mescla com cache existente. Se False, sobrescreve.
        """
        cache_key = f"user:{user_id}"
        
        if merge and cache_key in self._tier_cache:
            existing = self._tier_cache[cache_key].get('models', {})
            # Mescla: novos tiers sobrescrevem existentes, mas mantém outros
            existing.update(tiers)
            tiers = existing
            logger.debug(f"Cache mesclado: {len(tiers)} tiers totais")
        
        self._tier_cache[cache_key] = {
            'last_updated': datetime.now(),
            'models': tiers
        }
    
    def clear_cache(self, user_id: Optional[str] = None):
        """
        Limpa cache (para um usuário específico ou todos)
        
        Args:
            user_id: ID do usuário (None para limpar todos)
        """
        if user_id:
            cache_key = f"user:{user_id}"
            self._tier_cache.pop(cache_key, None)
        else:
            self._tier_cache.clear()
    
    async def detect_all_models(
        self,
        user_id: str,
        api_keys: List[Dict[str, Any]]
    ) -> Dict[str, ModelTierInfo]:
        """
        Detecta tier de todos os modelos de todas as chaves de API
        
        Args:
            user_id: ID do usuário
            api_keys: Lista de dicts com {service, api_key, models: [{name, category, ...}]}
            
        Returns:
            Dicionário {f"{service}:{model_name}": ModelTierInfo}
        """
        # Verifica cache primeiro
        cached = self.get_cached_tiers(user_id)
        
        # Verifica quais serviços estão sendo detectados agora
        services_to_detect = {api_key_data.get('service') for api_key_data in api_keys if api_key_data.get('service')}
        
        if cached:
            # Verifica se o cache tem dados válidos (não apenas "unknown") para os serviços sendo detectados
            valid_tiers = {k: v for k, v in cached.items() if v.tier and v.tier != "unknown"}
            
            # Verifica tiers válidos por serviço
            tiers_by_service = {}
            valid_tiers_by_service = {}
            for service in services_to_detect:
                service_tiers = {k: v for k, v in cached.items() if k.startswith(f"{service}:")}
                valid_service_tiers = {k: v for k, v in service_tiers.items() if v.tier and v.tier != "unknown"}
                tiers_by_service[service] = service_tiers
                valid_tiers_by_service[service] = valid_service_tiers
            
            # Para cada serviço sendo detectado, verifica se precisa forçar nova detecção
            services_to_clear = []
            for service in services_to_detect:
                service_tiers = tiers_by_service.get(service, {})
                valid_service_tiers = valid_tiers_by_service.get(service, {})
                
                # Se o serviço tem tiers no cache mas todos são "unknown", força nova detecção
                if service_tiers and not valid_service_tiers:
                    logger.info(f"Cache {service} contém apenas 'unknown', forçando nova detecção para {service} (usuário {user_id})")
                    services_to_clear.append(service)
            
            # Remove tiers "unknown" dos serviços que precisam de nova detecção
            if services_to_clear:
                for key in list(cached.keys()):
                    for service in services_to_clear:
                        if key.startswith(f"{service}:") and cached[key].tier == "unknown":
                            del cached[key]
                            break
                
                # Se cache ficou vazio, limpa completamente
                if not cached:
                    self.clear_cache(user_id)
                    cached = None
                else:
                    # Se ainda há tiers válidos de outros serviços, continua para detectar os serviços que foram limpos
                    remaining_valid = {k: v for k, v in cached.items() if v.tier and v.tier != "unknown"}
                    if remaining_valid:
                        logger.info(f"Cache tem {len(remaining_valid)} tiers válidos (após limpar {len(services_to_clear)} serviços), forçando nova detecção para: {services_to_clear}")
                        # Continua para detectar os serviços que foram limpos
                    else:
                        # Cache ficou sem tiers válidos, limpa completamente
                        self.clear_cache(user_id)
                        cached = None
            elif valid_tiers:
                # Verifica se há tiers válidos ESPECIFICAMENTE para os serviços sendo detectados
                valid_tiers_for_detecting_services = {}
                for service in services_to_detect:
                    service_valid = valid_tiers_by_service.get(service, {})
                    valid_tiers_for_detecting_services.update(service_valid)
                
                # Verifica se TODOS os serviços sendo detectados têm tiers válidos no cache
                all_services_have_valid = all(
                    bool(valid_tiers_by_service.get(service, {})) 
                    for service in services_to_detect
                )
                
                if all_services_have_valid and valid_tiers_for_detecting_services:
                    # Todos os serviços têm tiers válidos, retorna cache
                    logger.info(f"Retornando {len(valid_tiers_for_detecting_services)} tiers válidos do cache para serviços {services_to_detect} (usuário {user_id})")
                    return cached
                else:
                    # Alguns serviços não têm tiers válidos ou não têm tiers no cache, força nova detecção
                    services_without_valid = [
                        s for s in services_to_detect 
                        if not valid_tiers_by_service.get(s, {})
                    ]
                    logger.info(f"Serviços {services_without_valid} não têm tiers válidos no cache, forçando nova detecção (cache tem {len(valid_tiers)} tiers válidos de outros serviços)")
                    # Remove tiers "unknown" desses serviços do cache
                    for key in list(cached.keys()):
                        for service in services_without_valid:
                            if key.startswith(f"{service}:") and cached[key].tier == "unknown":
                                del cached[key]
                                break
                    # Continua para detectar os serviços que foram limpos
            else:
                logger.info(f"Cache contém apenas 'unknown', forçando nova detecção para usuário {user_id}")
                # Limpa cache se só tem "unknown"
                self.clear_cache(user_id)
                cached = None
        
        logger.info(f"Iniciando detecção de tiers para {len(api_keys)} chaves de API")
        
        all_tiers = {}
        
        # Processa cada chave de API
        for api_key_data in api_keys:
            service = api_key_data.get('service')
            api_key = api_key_data.get('api_key')
            models = api_key_data.get('models', [])
            
            if not api_key or not service:
                continue
            
            # Usa método auxiliar para processamento paralelo (Gemini) ou sequencial (outros)
            service_tiers = await self._detect_models_batch(
                service=service,
                api_key=api_key,
                models=models,
                user_id=user_id,
                cached=cached
            )
            all_tiers.update(service_tiers)
        
        # Salva no cache (mesclando com existente)
        self.cache_tiers(user_id, all_tiers, merge=True)
        
        logger.info(f"Detecção concluída: {len(all_tiers)} modelos processados")
        return all_tiers
    
    async def _detect_models_batch(
        self,
        service: str,
        api_key: str,
        models: List[Dict[str, Any]],
        user_id: str,
        cached: Optional[Dict[str, ModelTierInfo]] = None
    ) -> Dict[str, ModelTierInfo]:
        """
        Detecta tiers em lotes paralelos (Gemini) ou sequencial (outros serviços)
        
        Args:
            service: Nome do serviço
            api_key: Chave de API
            models: Lista de modelos [{name, category, ...}]
            user_id: ID do usuário
            cached: Cache existente para verificação parcial
            
        Returns:
            Dicionário {f"{service}:{model_name}": ModelTierInfo}
        """
        all_tiers = {}
        
        # Para Gemini, usa processamento paralelo em lotes
        if service == "gemini":
            batch_size = 5  # 5 modelos por vez
            semaphore = asyncio.Semaphore(batch_size)  # Limita concorrência
            
            async def detect_with_semaphore(model_info):
                async with semaphore:
                    model_name = model_info.get('name')
                    category = model_info.get('category', 'text')
                    
                    if not model_name:
                        return None
                    
                    # Verifica cache primeiro
                    cache_key = f"{service}:{model_name}"
                    if cached and cache_key in cached:
                        cached_tier = cached[cache_key]
                        if cached_tier.tier != "unknown":
                            logger.debug(f"Usando tier do cache para {cache_key}: {cached_tier.tier}")
                            return (cache_key, cached_tier)
                    
                    try:
                        logger.info(f"Detectando tier para {service}:{model_name} (categoria: {category})")
                        tier_info = await self.detect_model_tier(
                            api_key=api_key,
                            service=service,
                            model_name=model_name,
                            category=category
                        )
                        logger.info(f"Tier detectado para {cache_key}: {tier_info.tier} (método: {tier_info.detection_method}, confiança: {tier_info.confidence})")
                        if tier_info.tier == "unknown":
                            logger.warning(f"Tier 'unknown' detectado para {cache_key} - método: {tier_info.detection_method}")
                        return (cache_key, tier_info)
                    except Exception as e:
                        logger.error(f"Erro ao detectar tier de {service}:{model_name}: {e}", exc_info=True)
                        return (cache_key, ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="unknown",
                            detection_method="error",
                            confidence=0.0,
                            available=True,
                            last_checked=datetime.now()
                        ))
            
            # Processa todos os modelos em paralelo (limitado pelo semáforo)
            logger.info(f"Iniciando detecção paralela para {len(models)} modelos Gemini")
            tasks = [detect_with_semaphore(model_info) for model_info in models]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = 0
            unknown_count = 0
            error_count = 0
            for result in results:
                if result and isinstance(result, tuple):
                    cache_key, tier_info = result
                    all_tiers[cache_key] = tier_info
                    if tier_info.tier != "unknown":
                        successful += 1
                    else:
                        unknown_count += 1
                elif isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Exceção não tratada no processamento paralelo: {result}")
            
            logger.info(f"Detecção Gemini concluída: {successful} com tier válido, {unknown_count} com 'unknown', {error_count} erros")
        else:
            # Para outros serviços, mantém processamento sequencial
            for model_info in models:
                model_name = model_info.get('name')
                category = model_info.get('category', 'text')
                
                if not model_name:
                    continue
                
                # Verifica cache primeiro
                cache_key = f"{service}:{model_name}"
                if cached and cache_key in cached:
                    cached_tier = cached[cache_key]
                    if cached_tier.tier != "unknown":
                        logger.debug(f"Usando tier do cache para {cache_key}: {cached_tier.tier}")
                        all_tiers[cache_key] = cached_tier
                        continue
                
                try:
                    logger.info(f"Detectando tier para {service}:{model_name} (categoria: {category})")
                    tier_info = await self.detect_model_tier(
                        api_key=api_key,
                        service=service,
                        model_name=model_name,
                        category=category
                    )
                    
                    all_tiers[cache_key] = tier_info
                    logger.info(f"Tier detectado para {cache_key}: {tier_info.tier} (método: {tier_info.detection_method}, confiança: {tier_info.confidence})")
                    if tier_info.tier == "unknown":
                        logger.warning(f"Tier 'unknown' detectado para {cache_key} - método: {tier_info.detection_method}")
                    
                    # Pequeno delay para evitar rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Erro ao detectar tier de {service}:{model_name}: {e}", exc_info=True)
                    # Cria tier_info com unknown em caso de erro
                    tier_info = ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=True,
                        last_checked=datetime.now()
                    )
                    all_tiers[cache_key] = tier_info
        
        return all_tiers
    
    async def detect_model_tier(
        self,
        api_key: str,
        service: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """
        Detecta tier de um modelo específico
        
        Args:
            api_key: Chave de API
            service: Nome do serviço (gemini, openrouter, groq, together)
            model_name: Nome do modelo
            category: Categoria do modelo (text, audio, video, image, etc.)
            
        Returns:
            ModelTierInfo com informações do tier
        """
        # Roteia para método específico baseado na categoria
        if category in ['text', 'reasoning', 'code']:
            return await self.test_text_model(api_key, service, model_name, category)
        elif category in ['image', 'vision']:
            return await self.test_vision_model(api_key, service, model_name, category)
        elif category == 'video':
            return await self.test_video_model(api_key, service, model_name, category)
        elif category == 'audio':
            return await self.test_audio_model(api_key, service, model_name, category)
        elif category == 'multimodal':
            # Tenta teste de texto primeiro (multimodal geralmente aceita)
            try:
                return await self.test_text_model(api_key, service, model_name, category)
            except:
                return ModelTierInfo(
                    model_name=model_name,
                    service=service,
                    category=category,
                    tier="unknown",
                    detection_method="multimodal_fallback",
                    confidence=0.5,
                    available=True,
                    last_checked=datetime.now()
                )
        else:
            # Fallback: tenta teste de texto
            return await self.test_text_model(api_key, service, model_name, category)
    
    async def test_text_model(
        self,
        api_key: str,
        service: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """
        Testa modelo de texto/reasoning através de requisição mínima
        
        Args:
            api_key: Chave de API
            service: Nome do serviço
            model_name: Nome do modelo
            category: Categoria
            
        Returns:
            ModelTierInfo
        """
        try:
            if service == "gemini":
                return await self._test_gemini_model(api_key, model_name, category)
            elif service == "openrouter":
                return await self._test_openrouter_model(api_key, model_name, category)
            elif service == "groq":
                return await self._test_groq_model(api_key, model_name, category)
            elif service == "together":
                return await self._test_together_model(api_key, model_name, category)
            else:
                return ModelTierInfo(
                    model_name=model_name,
                    service=service,
                    category=category,
                    tier="unknown",
                    detection_method="unsupported_service",
                    confidence=0.0,
                    available=False,
                    last_checked=datetime.now()
                )
        except Exception as e:
            logger.error(f"Erro ao testar modelo de texto {service}:{model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service=service,
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=True,
                last_checked=datetime.now()
            )
    
    async def _test_gemini_model(
        self,
        api_key: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo Gemini com retry e timeout reduzido"""
        max_retries = 2
        timeout_seconds = 8.0  # Reduzido de 15s para 8s
        
        for attempt in range(max_retries + 1):  # 0, 1, 2 = 3 tentativas total
            try:
                from google import genai
                
                # Executa em thread pool para não bloquear
                loop = asyncio.get_event_loop()
                
                def test_model_sync():
                    try:
                        client = genai.Client(api_key=api_key)
                        # Faz requisição mínima para testar o modelo
                        response = client.models.generate_content(
                            model=model_name,
                            contents="test"
                        )
                        return response
                    except Exception as sync_error:
                        # Re-raise para ser capturado no nível assíncrono
                        raise sync_error
                
                # Executa com timeout reduzido
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, test_model_sync),
                        timeout=timeout_seconds
                    )
                    logger.info(f"Requisição bem-sucedida para {model_name} (tentativa {attempt + 1})")
                    
                    # Verifica se a resposta tem conteúdo válido
                    if not response:
                        logger.warning(f"Resposta vazia para {model_name}")
                        if attempt < max_retries:
                            wait_time = (attempt + 1) * 0.5
                            logger.debug(f"Tentando novamente em {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return ModelTierInfo(
                                model_name=model_name,
                                service="gemini",
                                category=category,
                                tier="unknown",
                                detection_method="empty_response",
                                confidence=0.0,
                                available=True,
                                last_checked=datetime.now()
                            )
                    
                    # Sucesso - retorna tier
                    tier = "free"
                    confidence = 0.7
                    quota_info = {}
                    if hasattr(response, 'headers'):
                        quota_info = analyze_response_headers(response.headers)
                    
                    return ModelTierInfo(
                        model_name=model_name,
                        service="gemini",
                        category=category,
                        tier=tier,
                        detection_method="test_request",
                        confidence=confidence,
                        available=True,
                        quota_info=quota_info if quota_info else None,
                        last_checked=datetime.now()
                    )
                    
                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 0.5  # Backoff: 0.5s, 1s
                        logger.warning(f"Timeout ao testar {model_name} (tentativa {attempt + 1}/{max_retries + 1}), tentando novamente em {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Timeout ao testar modelo Gemini {model_name} após {max_retries + 1} tentativas")
                        return ModelTierInfo(
                            model_name=model_name,
                            service="gemini",
                            category=category,
                            tier="unknown",
                            detection_method="timeout",
                            confidence=0.0,
                            available=True,
                            last_checked=datetime.now()
                        )
            except Exception as e:
                error_str = str(e)
                error_repr = repr(e)
                error_type = type(e).__name__
                logger.warning(f"Erro ao testar modelo Gemini {model_name} (tentativa {attempt + 1}/{max_retries + 1}): {error_type} - {error_str[:300]}")
                logger.debug(f"Detalhes completos do erro para {model_name}: {error_repr[:500]}", exc_info=True)
                
                # Analisa tipo de erro
                # Trata 404 primeiro - modelo não encontrado ou não suporta generateContent
                if '404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower() or 'not supported for generateContent' in error_str:
                    # Modelo não encontrado ou não suporta generateContent
                    # Não faz retry - retorna imediatamente
                    logger.info(f"Modelo {model_name} não suporta generateContent ou não encontrado (404). Retornando 'unknown' sem retry.")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="gemini",
                        category=category,
                        tier="unknown",
                        detection_method="error_not_supported",
                        confidence=0.5,
                        available=False,
                        last_checked=datetime.now()
                    )
                elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                    # Rate limit ou quota excedida - indica free tier com limite atingido
                    # Não faz retry - retorna imediatamente como "free"
                    logger.info(f"Modelo {model_name} retornou 429 (quota excedida). Retornando 'free' sem retry.")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="gemini",
                        category=category,
                        tier="free",
                        detection_method="error_quota_exceeded",
                        confidence=0.8,
                        available=True,
                        last_checked=datetime.now()
                    )
                elif '402' in error_str or 'billing' in error_str.lower() or 'payment' in error_str.lower():
                    # Erro de billing = paid tier sem créditos
                    # Não faz retry - retorna imediatamente
                    logger.info(f"Modelo {model_name} retornou erro de billing (402). Retornando 'paid' sem retry.")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="gemini",
                        category=category,
                        tier="paid",
                        detection_method="error_billing",
                        confidence=0.9,
                        available=False,
                        last_checked=datetime.now()
                    )
                else:
                    # Outro erro - tenta novamente se ainda há tentativas
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 0.5
                        logger.warning(f"Erro ao testar {model_name} (tentativa {attempt + 1}/{max_retries + 1}), tentando novamente em {wait_time}s... Erro: {error_str[:200]}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Todas as tentativas falharam
                        logger.error(f"Todas as tentativas falharam para {model_name}. Último erro ({error_type}): {error_str[:500]}", exc_info=True)
                        return ModelTierInfo(
                            model_name=model_name,
                            service="gemini",
                            category=category,
                            tier="unknown",
                            detection_method="error",
                            confidence=0.0,
                            available=False,
                            last_checked=datetime.now()
                        )
        
        # Se chegou aqui, todas as tentativas falharam sem retornar
        return ModelTierInfo(
            model_name=model_name,
            service="gemini",
            category=category,
            tier="unknown",
            detection_method="error",
            confidence=0.0,
            available=False,
            last_checked=datetime.now()
        )
    
    async def _test_openrouter_model(
        self,
        api_key: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo OpenRouter - consulta endpoint de pricing"""
        try:
            import httpx
            
            logger.info(f"Iniciando detecção de tier para OpenRouter: {model_name}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # OpenRouter explicita modelos free com sufixo ":free"
                # Se estiver presente, é o sinal mais confiável e evita chamadas adicionais
                if model_name.endswith(":free"):
                    logger.info(f"OpenRouter {model_name}: tier=free (sufixo :free detectado)")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="openrouter",
                        category=category,
                        tier="free",
                        detection_method="free_suffix",
                        confidence=0.95,
                        available=True,
                        last_checked=datetime.now()
                    )

                # Consulta endpoint de modelos para obter pricing
                models_response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com",
                        "X-Title": "Translation System"
                    }
                )
                
                logger.info(f"Resposta do endpoint de modelos OpenRouter: status={models_response.status_code}")
                
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    models_list = models_data.get("data", [])
                    
                    # Procura o modelo na lista
                    model_found = False
                    for model_data in models_list:
                        if model_data.get("id") == model_name:
                            model_found = True
                            pricing = model_data.get("pricing", {})
                            prompt_price = pricing.get("prompt", "0")
                            completion_price = pricing.get("completion", "0")
                            
                            try:
                                prompt_val = float(prompt_price) if prompt_price else 0
                                completion_val = float(completion_price) if completion_price else 0
                                
                                if prompt_val == 0 and completion_val == 0:
                                    tier = "free"
                                    confidence = 0.9
                                else:
                                    tier = "paid"
                                    confidence = 0.9
                                
                                logger.info(f"OpenRouter {model_name}: tier={tier} (encontrado no endpoint de pricing)")
                                # Retorna imediatamente quando encontra na lista
                                return ModelTierInfo(
                                    model_name=model_name,
                                    service="openrouter",
                                    category=category,
                                    tier=tier,
                                    detection_method="pricing_endpoint",
                                    confidence=confidence,
                                    available=True,
                                    cost_info={
                                        "prompt_per_1k": prompt_val,
                                        "completion_per_1k": completion_val
                                    },
                                    last_checked=datetime.now()
                                )
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Erro ao processar pricing para {model_name}: {e}")
                                break  # Sai do loop e tenta requisição de teste
                    
                    if not model_found:
                        logger.info(f"Modelo {model_name} não encontrado na lista OpenRouter, tentando requisição de teste")
                
                # Se não encontrou na lista OU erro ao processar pricing, tenta teste de requisição
                test_response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://github.com",
                        "X-Title": "Translation System",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                
                logger.info(f"Resposta do teste OpenRouter para {model_name}: status={test_response.status_code}")
                
                if test_response.status_code == 200:
                    # Sucesso - assume free (OpenRouter geralmente tem free tier)
                    logger.info(f"OpenRouter {model_name}: tier=free (test_request bem-sucedido)")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="openrouter",
                        category=category,
                        tier="free",
                        detection_method="test_request",
                        confidence=0.7,
                        available=True,
                        last_checked=datetime.now()
                    )
                elif test_response.status_code == 402:
                    # Payment required = paid
                    logger.info(f"OpenRouter {model_name}: tier=paid (payment required)")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="openrouter",
                        category=category,
                        tier="paid",
                        detection_method="error_payment_required",
                        confidence=0.9,
                        available=False,
                        last_checked=datetime.now()
                    )
                else:
                    logger.warning(f"OpenRouter {model_name}: status={test_response.status_code}, retornando unknown")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="openrouter",
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=False,
                        last_checked=datetime.now()
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao testar OpenRouter {model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service="openrouter",
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )
    
    async def _test_groq_model(
        self,
        api_key: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo Groq"""
        try:
            import httpx
            
            logger.debug(f"Iniciando detecção de tier para Groq: {model_name}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Groq geralmente tem free tier, então tenta requisição
                test_response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                
                logger.debug(f"Resposta do teste Groq para {model_name}: status={test_response.status_code}")
                
                if test_response.status_code == 200:
                    # Groq: extrai headers de rate limit para melhorar confiabilidade do tier
                    quota_info = analyze_response_headers(test_response)
                    limit_requests = quota_info.get("limit_requests") if quota_info else None

                    tier = "free"
                    detection_method = "test_request"
                    confidence = 0.8

                    # Se temos limite de requests numérico, ajusta confiança com base no tamanho do limite
                    if isinstance(limit_requests, int):
                        if limit_requests < 20000:
                            confidence = 0.9
                            detection_method = "rate_limit_headers"
                        else:
                            # Limite alto pode indicar tier superior; ainda assim mantemos "free" por padrão
                            confidence = 0.7
                            detection_method = "test_request"

                    logger.info(
                        f"Groq {model_name}: tier={tier} (limit_requests={limit_requests}, método={detection_method}, confiança={confidence})"
                    )
                    return ModelTierInfo(
                        model_name=model_name,
                        service="groq",
                        category=category,
                        tier=tier,
                        detection_method=detection_method,
                        confidence=confidence,
                        available=True,
                        quota_info=quota_info if quota_info else None,
                        last_checked=datetime.now()
                    )
                elif test_response.status_code == 402:
                    logger.info(f"Groq {model_name}: tier=paid (payment required)")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="groq",
                        category=category,
                        tier="paid",
                        detection_method="error_payment_required",
                        confidence=0.9,
                        available=False,
                        last_checked=datetime.now()
                    )
                else:
                    logger.warning(f"Groq {model_name}: status={test_response.status_code}, retornando unknown")
                    return ModelTierInfo(
                        model_name=model_name,
                        service="groq",
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=False,
                        last_checked=datetime.now()
                    )
        except Exception as e:
            logger.error(f"Erro ao testar Groq {model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service="groq",
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )
    
    async def _test_together_model(
        self,
        api_key: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo Together AI"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                test_response = await client.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                
                if test_response.status_code == 200:
                    # Together geralmente tem free tier limitado
                    return ModelTierInfo(
                        model_name=model_name,
                        service="together",
                        category=category,
                        tier="free",
                        detection_method="test_request",
                        confidence=0.7,
                        available=True,
                        last_checked=datetime.now()
                    )
                elif test_response.status_code == 402:
                    return ModelTierInfo(
                        model_name=model_name,
                        service="together",
                        category=category,
                        tier="paid",
                        detection_method="error_payment_required",
                        confidence=0.9,
                        available=False,
                        last_checked=datetime.now()
                    )
                else:
                    return ModelTierInfo(
                        model_name=model_name,
                        service="together",
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=False,
                        last_checked=datetime.now()
                    )
        except Exception as e:
            logger.error(f"Erro ao testar Together {model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service="together",
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )
    
    async def test_vision_model(
        self,
        api_key: str,
        service: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo de visão/imagem"""
        try:
            if service == "gemini":
                from google import genai
                client = genai.Client(api_key=api_key)
                
                # Cria imagem mínima
                image_base64 = create_minimal_image_base64()
                
                # Tenta requisição com imagem
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[{
                            "parts": [
                                {"text": "describe"},
                                {"inline_data": {"mime_type": "image/png", "data": image_base64}}
                            ]
                        }]
                    )
                    
                    # Sucesso = provavelmente free
                    return ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="free",
                        detection_method="test_request_image",
                        confidence=0.7,
                        available=True,
                        last_checked=datetime.now()
                    )
                except Exception as e:
                    error_str = str(e)
                    # Analisa tipo de erro
                    if '404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower() or 'not supported for generateContent' in error_str:
                        # Modelo não suporta ou não encontrado
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="unknown",
                            detection_method="error_not_supported",
                            confidence=0.5,
                            available=False,
                            last_checked=datetime.now()
                        )
                    elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                        # Quota excedida = free tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="free",
                            detection_method="error_quota_exceeded",
                            confidence=0.8,
                            available=True,
                            last_checked=datetime.now()
                        )
                    elif '402' in error_str or 'billing' in error_str.lower() or 'payment' in error_str.lower():
                        # Erro de billing = paid tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="paid",
                            detection_method="error_billing",
                            confidence=0.9,
                            available=False,
                            last_checked=datetime.now()
                        )
                    
                    # Se falhar com imagem, tenta apenas texto (alguns vision aceitam)
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents="test"
                        )
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="free",
                            detection_method="test_request_text_fallback",
                            confidence=0.6,
                            available=True,
                            last_checked=datetime.now()
                        )
                    except Exception as e2:
                        error_str2 = str(e2)
                        # Analisa erro do fallback também
                        if '404' in error_str2 or 'NOT_FOUND' in error_str2 or 'not found' in error_str2.lower() or 'not supported for generateContent' in error_str2:
                            return ModelTierInfo(
                                model_name=model_name,
                                service=service,
                                category=category,
                                tier="unknown",
                                detection_method="error_not_supported",
                                confidence=0.5,
                                available=False,
                                last_checked=datetime.now()
                            )
                        elif '429' in error_str2 or 'RESOURCE_EXHAUSTED' in error_str2 or 'quota' in error_str2.lower():
                            return ModelTierInfo(
                                model_name=model_name,
                                service=service,
                                category=category,
                                tier="free",
                                detection_method="error_quota_exceeded",
                                confidence=0.8,
                                available=True,
                                last_checked=datetime.now()
                            )
                        elif '402' in error_str2 or 'billing' in error_str2.lower() or 'payment' in error_str2.lower():
                            return ModelTierInfo(
                                model_name=model_name,
                                service=service,
                                category=category,
                                tier="paid",
                                detection_method="error_billing",
                                confidence=0.9,
                                available=False,
                                last_checked=datetime.now()
                            )
                        # Outro erro - marca como unknown
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="unknown",
                            detection_method="error",
                            confidence=0.0,
                            available=False,
                            last_checked=datetime.now()
                        )
            else:
                # Para outros serviços, usa teste de texto
                return await self.test_text_model(api_key, service, model_name, category)
                
        except Exception as e:
            logger.error(f"Erro ao testar modelo vision {service}:{model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service=service,
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )
    
    async def test_video_model(
        self,
        api_key: str,
        service: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo de vídeo"""
        try:
            if service == "gemini":
                from google import genai
                client = genai.Client(api_key=api_key)
                
                # Tenta requisição mínima para verificar se modelo responde
                # Modelos Veo podem não suportar generateContent, mas podemos detectar pelo erro
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents="test"
                    )
                    # Se funcionou, é free
                    return ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="free",
                        detection_method="test_request",
                        confidence=0.7,
                        available=True,
                        last_checked=datetime.now()
                    )
                except Exception as e:
                    error_str = str(e)
                    # Analisa tipo de erro
                    if '404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower() or 'not supported for generateContent' in error_str:
                        # Modelo não suporta generateContent (normal para Veo)
                        # Modelos Veo são modelos premium de geração de vídeo, geralmente pagos
                        # Mas como não conseguimos testar diretamente, assumimos como "paid" com confiança média
                        logger.info(f"Modelo Veo {model_name} não suporta generateContent. Assumindo como 'paid' (modelos Veo são premium).")
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="paid",
                            detection_method="veo_premium_assumption",
                            confidence=0.7,
                            available=True,
                            last_checked=datetime.now()
                        )
                    elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                        # Quota excedida = free tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="free",
                            detection_method="error_quota_exceeded",
                            confidence=0.8,
                            available=True,
                            last_checked=datetime.now()
                        )
                    elif '402' in error_str or 'billing' in error_str.lower() or 'payment' in error_str.lower():
                        # Erro de billing = paid tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="paid",
                            detection_method="error_billing",
                            confidence=0.9,
                            available=False,
                            last_checked=datetime.now()
                        )
                    # Outro erro - marca como unknown
                    return ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=False,
                        last_checked=datetime.now()
                    )
            else:
                # Para outros serviços, usa teste de texto
                return await self.test_text_model(api_key, service, model_name, category)
        except Exception as e:
            logger.error(f"Erro ao testar modelo video {service}:{model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service=service,
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )
    
    async def test_audio_model(
        self,
        api_key: str,
        service: str,
        model_name: str,
        category: str
    ) -> ModelTierInfo:
        """Testa modelo de áudio"""
        try:
            if service == "gemini":
                from google import genai
                client = genai.Client(api_key=api_key)
                
                # Tenta requisição mínima para verificar se modelo responde
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents="a"
                    )
                    # Se funcionou, é free
                    return ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="free",
                        detection_method="test_request_audio",
                        confidence=0.7,
                        available=True,
                        last_checked=datetime.now()
                    )
                except Exception as e:
                    error_str = str(e)
                    # Analisa tipo de erro
                    if '404' in error_str or 'NOT_FOUND' in error_str or 'not found' in error_str.lower() or 'not supported for generateContent' in error_str:
                        # Modelo não suporta generateContent (normal para alguns modelos de áudio)
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="unknown",
                            detection_method="error_not_supported",
                            confidence=0.5,
                            available=False,
                            last_checked=datetime.now()
                        )
                    elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                        # Quota excedida = free tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="free",
                            detection_method="error_quota_exceeded",
                            confidence=0.8,
                            available=True,
                            last_checked=datetime.now()
                        )
                    elif '402' in error_str or 'billing' in error_str.lower() or 'payment' in error_str.lower():
                        # Erro de billing = paid tier
                        return ModelTierInfo(
                            model_name=model_name,
                            service=service,
                            category=category,
                            tier="paid",
                            detection_method="error_billing",
                            confidence=0.9,
                            available=False,
                            last_checked=datetime.now()
                        )
                    # Outro erro - marca como unknown
                    return ModelTierInfo(
                        model_name=model_name,
                        service=service,
                        category=category,
                        tier="unknown",
                        detection_method="error",
                        confidence=0.0,
                        available=False,
                        last_checked=datetime.now()
                    )
            else:
                # Para outros serviços, usa teste de texto
                return await self.test_text_model(api_key, service, model_name, category)
                
        except Exception as e:
            logger.error(f"Erro ao testar modelo audio {service}:{model_name}: {e}")
            return ModelTierInfo(
                model_name=model_name,
                service=service,
                category=category,
                tier="unknown",
                detection_method="error",
                confidence=0.0,
                available=False,
                last_checked=datetime.now()
            )


# Instância global do detector
_tier_detector_instance: Optional[ModelTierDetector] = None


def get_tier_detector() -> ModelTierDetector:
    """Retorna instância singleton do detector"""
    global _tier_detector_instance
    if _tier_detector_instance is None:
        _tier_detector_instance = ModelTierDetector()
    return _tier_detector_instance
