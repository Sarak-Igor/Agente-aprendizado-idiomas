from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database import ApiKey, Video, User
from app.api.routes.auth import get_current_user
from app.services.encryption import encryption_service
from app.services.gemini_service import GeminiService
from app.services.model_router import ModelRouter
from app.services.api_status_checker import ApiStatusChecker
from app.services.model_tier_detector import get_tier_detector
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/api/keys", tags=["api-keys"])
logger = logging.getLogger(__name__)


class ModelStatus(BaseModel):
    name: str
    available: bool
    blocked: bool
    status: str
    category: Optional[str] = None  # text, reasoning, audio, video, code, multimodal
    tier: Optional[str] = None  # "free", "paid", "unknown"
    tier_reason: Optional[str] = None  # Motivo curto quando tier="unknown": "Não testável", "Indisponível", "Ambíguo"
    quota_used: Optional[int] = None  # Tokens usados (free)
    quota_limit: Optional[int] = None  # Limite tokens (free)
    cost_last_24h: Optional[float] = None  # Custo $ (paid)


def _get_unknown_tier_reason(tier_info) -> str:
    """
    Motivo curto para tier desconhecido.
    Regras:
    - Não testável: método indica incompatibilidade com endpoint (not_supported / not_testable)
    - Indisponível: tier_info.available == False
    - Ambíguo: fallback quando nada disso se aplica
    """
    try:
        detection_method = getattr(tier_info, "detection_method", None) or ""
        available = getattr(tier_info, "available", True)

        method_lower = str(detection_method).lower()
        if "not_testable" in method_lower or "not_supported" in method_lower:
            return "Não testável"
        if available is False:
            return "Indisponível"
        return "Ambíguo"
    except Exception:
        return "Ambíguo"


class ApiKeyStatus(BaseModel):
    service: str
    is_valid: bool
    models_status: List[ModelStatus]
    available_models: List[str]
    blocked_models: List[str]
    error: Optional[str] = None
    models_by_category: Optional[Dict[str, List[ModelStatus]]] = None  # Agrupamento por categoria


# Rebuild do modelo para resolver forward references
ApiKeyStatus.model_rebuild()


class ApiKeyCheckRequest(BaseModel):
    api_key: str
    service: str = "gemini"


@router.post("/check-status", response_model=ApiKeyStatus)
async def check_api_key_status(
    request: ApiKeyCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Verifica status e cotas de uma chave de API
    Suporta: gemini, openrouter, groq, together
    """
    try:
        # Verifica Gemini (implementação específica)
        if request.service == "gemini":
            try:
                # Cria cliente Gemini primeiro para carregar modelos dinamicamente
                from google import genai
                gemini_client = genai.Client(api_key=request.api_key)
                
                # Cria ModelRouter com cliente para carregar modelos dinamicamente
                # validate_on_init=False para não validar automaticamente (será validado depois se necessário)
                model_router = ModelRouter(validate_on_init=False, gemini_client=gemini_client)
                # Valida modelos de forma não-bloqueante
                # Não valida todos de uma vez para evitar bloqueios incorretos
                try:
                    model_router.validate_available_models(gemini_client)
                except Exception as e:
                    logger.debug(f"Validação de modelos falhou (não crítico): {e}")
                
                gemini_service = GeminiService(
                    request.api_key,
                    model_router,
                    validate_models=False  # Não valida novamente - já foi validado acima
                )
                
                # Obtém status dos modelos
                models_status = []
                available_models = model_router.get_validated_models()
                blocked_models = model_router.get_blocked_models_list()
                
                # Obtém lista de modelos do router (pode ter sido expandida dinamicamente)
                all_models = model_router.AVAILABLE_MODELS
                
                # IMPORTANTE: Exibe TODOS os modelos disponíveis, não apenas os validados
                # Modelos não validados aparecem como "unknown" mas não bloqueados
                # Apenas modelos realmente bloqueados (por quota) aparecem como bloqueados
                # Se nenhum modelo foi validado, assume que todos estão disponíveis (não bloqueados)
                if len(available_models) == 0:
                    # Considera todos os modelos como disponíveis (não validados, mas não bloqueados)
                    # Remove apenas os que estão realmente bloqueados
                    available_models = [m for m in all_models if m not in blocked_models]
                    logger.info(f"Validação não retornou modelos validados. Assumindo {len(available_models)} modelos disponíveis (não bloqueados)")
                
                # Cria status detalhado para cada modelo
                models_by_category = {}
                for model_name in all_models:
                    is_available = model_name in available_models
                    is_blocked = model_name in blocked_models
                    
                    # Lógica de status:
                    # - "available": validado e disponível
                    # - "blocked": realmente bloqueado (por quota)
                    # - "unknown": não validado, mas não bloqueado (pode ser usado)
                    if is_blocked:
                        status = "blocked"
                    elif is_available:
                        status = "available"
                    else:
                        status = "unknown"  # Não validado, mas não bloqueado
                    
                    # Categoriza o modelo
                    category = model_router.get_model_category(model_name)
                    
                    # Modelo está disponível se:
                    # - Foi validado como disponível, OU
                    # - Não está bloqueado (mesmo que não validado)
                    # IMPORTANTE: Modelos não validados são considerados disponíveis se não estão bloqueados
                    model_available = is_available or not is_blocked
                    
                    model_status = ModelStatus(
                        name=model_name,
                        available=model_available,
                        blocked=is_blocked,
                        status=status,
                        category=category
                    )
                    
                    models_status.append(model_status)
                    
                    # Agrupa por categoria
                    if category not in models_by_category:
                        models_by_category[category] = []
                    models_by_category[category].append(model_status)
                
                # Se há modelos disponíveis (validados ou não bloqueados), chave é válida
                has_available = len(available_models) > 0 or len(blocked_models) < len(all_models)
                
                return ApiKeyStatus(
                    service=request.service,
                    is_valid=has_available,
                    models_status=models_status,
                    available_models=available_models if available_models else [m for m in all_models if m not in blocked_models],
                    blocked_models=blocked_models,
                    error=None if has_available else "Nenhum modelo disponível. Verifique suas cotas de API no console do Google Cloud.",
                    models_by_category=models_by_category
                )
            except Exception as gemini_error:
                error_str = str(gemini_error)
                logger.error(f"Erro ao validar Gemini: {error_str}")
                
                # Se for erro de autenticação/chave inválida
                if '401' in error_str or '403' in error_str or 'invalid' in error_str.lower() or 'unauthorized' in error_str.lower() or 'permission' in error_str.lower():
                    return ApiKeyStatus(
                        service=request.service,
                        is_valid=False,
                        models_status=[],
                        available_models=[],
                        blocked_models=[],
                        error="Chave de API inválida ou sem permissão. Verifique se a chave está correta e se tem acesso aos modelos Gemini.",
                        models_by_category=None
                    )
                
                # Outros erros
                return ApiKeyStatus(
                    service=request.service,
                    is_valid=False,
                    models_status=[],
                    available_models=[],
                    blocked_models=[],
                    error=f"Erro ao validar modelos Gemini: {error_str[:200]}",
                    models_by_category=None
                )
        
        # Outras APIs (OpenRouter, Groq, Together)
        elif request.service in ["openrouter", "groq", "together"]:
            status_result = await ApiStatusChecker.check_status(request.service, request.api_key)
            
            # Converte para o formato esperado
            models_status = [
                ModelStatus(
                    name=model.get("name", "unknown"),
                    available=model.get("available", False),
                    blocked=model.get("blocked", False),
                    status=model.get("status", "unknown")
                )
                for model in status_result.get("models_status", [])
            ]
            
            return ApiKeyStatus(
                service=request.service,
                is_valid=status_result.get("is_valid", False),
                models_status=models_status,
                available_models=status_result.get("available_models", []),
                blocked_models=status_result.get("blocked_models", []),
                error=status_result.get("error"),
                models_by_category=None
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Serviço '{request.service}' não suportado. Serviços disponíveis: gemini, openrouter, groq, together"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        logger.error(f"Erro ao verificar status da chave API: {e}")
        
        # Se for erro de autenticação/chave inválida
        if '401' in error_str or '403' in error_str or 'invalid' in error_str.lower() or 'unauthorized' in error_str.lower():
            return ApiKeyStatus(
                service=request.service,
                is_valid=False,
                models_status=[],
                available_models=[],
                blocked_models=[],
                error="Chave de API inválida ou não autorizada",
                models_by_category=None
            )
        
        return ApiKeyStatus(
            service=request.service,
            is_valid=False,
            models_status=[],
            available_models=[],
            blocked_models=[],
            error=f"Erro ao verificar status: {error_str}",
            models_by_category=None
        )


@router.get("/list")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todas as chaves de API cadastradas do usuário atual (sem expor as chaves)
    """
    try:
        api_keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
        
        result = []
        for key in api_keys:
            result.append({
                "id": str(key.id),
                "service": key.service,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "updated_at": key.updated_at.isoformat() if key.updated_at else None
            })
        
        return {"api_keys": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Erro ao listar chaves API: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar chaves: {str(e)}")


class ApiKeyCreate(BaseModel):
    service: str
    api_key: str


class ApiKeyResponse(BaseModel):
    id: str
    service: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post("/", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria ou atualiza uma chave de API para o usuário atual
    """
    try:
        # Verifica se já existe chave para este serviço
        existing_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.service == key_data.service
        ).first()
        
        encrypted_key = encryption_service.encrypt(key_data.api_key)
        
        if existing_key:
            # Atualiza chave existente
            existing_key.encrypted_key = encrypted_key
            db.commit()
            db.refresh(existing_key)
            
            return ApiKeyResponse(
                id=str(existing_key.id),
                service=existing_key.service,
                created_at=existing_key.created_at.isoformat() if existing_key.created_at else None,
                updated_at=existing_key.updated_at.isoformat() if existing_key.updated_at else None
            )
        else:
            # Cria nova chave
            api_key = ApiKey(
                user_id=current_user.id,
                video_id=None,  # Chaves são do usuário, não do vídeo
                service=key_data.service,
                encrypted_key=encrypted_key
            )
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            
            return ApiKeyResponse(
                id=str(api_key.id),
                service=api_key.service,
                created_at=api_key.created_at.isoformat() if api_key.created_at else None,
                updated_at=api_key.updated_at.isoformat() if api_key.updated_at else None
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar/atualizar chave API: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar chave: {str(e)}")


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta uma chave de API do usuário atual
    """
    try:
        from uuid import UUID
        key_uuid = UUID(key_id)
        
        api_key = db.query(ApiKey).filter(
            ApiKey.id == key_uuid,
            ApiKey.user_id == current_user.id
        ).first()
        
        if not api_key:
            raise HTTPException(status_code=404, detail="Chave de API não encontrada")
        
        db.delete(api_key)
        db.commit()
        
        return {"message": "Chave de API deletada com sucesso"}
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de chave inválido")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao deletar chave API: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar chave: {str(e)}")


@router.delete("/service/{service}")
async def delete_api_key_by_service(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta uma chave de API pelo serviço do usuário atual
    """
    try:
        api_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.service == service
        ).first()
        
        if not api_key:
            raise HTTPException(status_code=404, detail=f"Chave de API para serviço '{service}' não encontrada")
        
        db.delete(api_key)
        db.commit()
        
        return {"message": f"Chave de API para serviço '{service}' deletada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao deletar chave API: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar chave: {str(e)}")


@router.post("/{service}/check-status-saved")
async def check_saved_api_key_status(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica status de uma chave de API salva do usuário atual
    """
    try:
        api_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.service == service
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=404, 
                detail=f"Chave de API para serviço '{service}' não encontrada"
            )
        
        # Descriptografa a chave
        decrypted_key = encryption_service.decrypt(api_key.encrypted_key)
        
        # Usa a mesma lógica de check-status mas com a chave salva
        if service == "gemini":
            try:
                # Cria cliente Gemini primeiro para carregar modelos dinamicamente
                from google import genai
                gemini_client = genai.Client(api_key=decrypted_key)
                
                # Cria ModelRouter com cliente para carregar modelos dinamicamente
                model_router = ModelRouter(validate_on_init=False, gemini_client=gemini_client)
                # Valida modelos de forma não-bloqueante
                try:
                    model_router.validate_available_models(gemini_client)
                except Exception as e:
                    logger.debug(f"Validação de modelos falhou (não crítico): {e}")
                
                gemini_service = GeminiService(
                    decrypted_key,
                    model_router,
                    validate_models=False  # Não valida novamente - já foi validado acima
                )
                
                models_status = []
                available_models = model_router.get_validated_models()
                blocked_models = model_router.get_blocked_models_list()
                
                # Obtém lista de modelos do router (pode ter sido expandida dinamicamente)
                all_models = model_router.AVAILABLE_MODELS
                
                # IMPORTANTE: Exibe TODOS os modelos disponíveis, não apenas os validados
                # Durante validação, modelos NÃO são bloqueados (apenas durante uso real)
                # Se nenhum modelo foi validado, assume que todos estão disponíveis (não bloqueados)
                # Remove apenas modelos que foram bloqueados durante uso real (não durante validação)
                if len(available_models) == 0:
                    # Considera todos os modelos como disponíveis (não validados, mas não bloqueados)
                    # Remove apenas os que estão realmente bloqueados (por uso real, não validação)
                    available_models = [m for m in all_models if m not in blocked_models]
                    logger.info(f"Validação não retornou modelos validados. Assumindo {len(available_models)} modelos disponíveis (não bloqueados durante validação)")
                
                # Agrupa modelos por categoria
                models_by_category = {}
                for model_name in all_models:
                    is_available = model_name in available_models
                    is_blocked = model_name in blocked_models
                    
                    # Lógica de status:
                    # - "available": validado e disponível
                    # - "blocked": realmente bloqueado (por quota)
                    # - "unknown": não validado, mas não bloqueado (pode ser usado)
                    if is_blocked:
                        status = "blocked"
                    elif is_available:
                        status = "available"
                    else:
                        status = "unknown"  # Não validado, mas não bloqueado
                    
                    # Categoriza o modelo
                    category = model_router.get_model_category(model_name)
                    
                    # Modelo está disponível se:
                    # - Foi validado como disponível, OU
                    # - Não está bloqueado (mesmo que não validado)
                    # IMPORTANTE: Modelos não validados são considerados disponíveis se não estão bloqueados
                    model_available = is_available or not is_blocked
                    
                    model_status = ModelStatus(
                        name=model_name,
                        available=model_available,
                        blocked=is_blocked,
                        status=status,
                        category=category
                    )
                    
                    models_status.append(model_status)
                    
                    # Agrupa por categoria
                    if category not in models_by_category:
                        models_by_category[category] = []
                    models_by_category[category].append(model_status)
                
                # Detecta tiers dos modelos
                try:
                    logger.info(f"Iniciando detecção de tiers para {len(models_status)} modelos do serviço {service}")
                    tier_detector = get_tier_detector()
                    
                    # Para Gemini, limpa cache se só tem "unknown" para forçar nova detecção
                    if service == "gemini":
                        cached = tier_detector.get_cached_tiers(str(current_user.id))
                        if cached:
                            gemini_tiers = {k: v for k, v in cached.items() if k.startswith("gemini:")}
                            valid_gemini_tiers = {k: v for k, v in gemini_tiers.items() if v.tier and v.tier != "unknown"}
                            if not valid_gemini_tiers and gemini_tiers:
                                logger.info(f"Cache Gemini contém apenas 'unknown', limpando para forçar nova detecção")
                                tier_detector.clear_cache(str(current_user.id))
                    
                    api_keys_data = [{
                        'service': service,
                        'api_key': decrypted_key,
                        'models': [{'name': ms.name, 'category': ms.category or 'text'} for ms in models_status]
                    }]
                    tiers = await tier_detector.detect_all_models(str(current_user.id), api_keys_data)
                    
                    logger.info(f"Tiers detectados: {len(tiers)} modelos processados")
                    if tiers:
                        sample_keys = list(tiers.keys())[:5]
                        logger.info(f"Exemplos de chaves de tier: {sample_keys}")
                        for key in sample_keys[:3]:
                            if key in tiers:
                                tier_info = tiers[key]
                                logger.info(f"  {key}: tier={tier_info.tier}, método={tier_info.detection_method}, confiança={tier_info.confidence}")
                    
                    # Conta tiers por tipo para debug
                    tier_counts = {}
                    for tier_info in tiers.values():
                        tier_type = tier_info.tier or "null"
                        tier_counts[tier_type] = tier_counts.get(tier_type, 0) + 1
                    logger.info(f"Distribuição de tiers: {tier_counts}")
                    
                    # Mescla informações de tier com modelos existentes
                    # Cria novos objetos ModelStatus com tier atualizado
                    updated_models_status = []
                    for model_status in models_status:
                        tier_key = f"{service}:{model_status.name}"
                        if tier_key in tiers:
                            tier_info = tiers[tier_key]
                            # Cria novo ModelStatus com tier atualizado
                            updated_model = ModelStatus(
                                name=model_status.name,
                                available=model_status.available,
                                blocked=model_status.blocked,
                                status=model_status.status,
                                category=model_status.category,
                                tier=tier_info.tier,
                                tier_reason=_get_unknown_tier_reason(tier_info) if tier_info.tier == "unknown" else None,
                                quota_used=tier_info.quota_info.get('remaining_tokens') if tier_info.quota_info else None,
                                quota_limit=tier_info.quota_info.get('limit_tokens') if tier_info.quota_info else None,
                                cost_last_24h=None if tier_info.cost_info else None
                            )
                            updated_models_status.append(updated_model)
                            if tier_info.tier != "unknown":
                                logger.debug(f"Tier para {model_status.name}: {tier_info.tier} (método: {tier_info.detection_method})")
                        else:
                            # Se não encontrou tier, marca como unknown para garantir que sempre tenha um valor
                            updated_model = ModelStatus(
                                name=model_status.name,
                                available=model_status.available,
                                blocked=model_status.blocked,
                                status=model_status.status,
                                category=model_status.category,
                                tier="unknown",
                                tier_reason="Ambíguo"
                            )
                            updated_models_status.append(updated_model)
                            logger.warning(f"Tier não encontrado para {model_status.name} (chave esperada: {tier_key})")
                    
                    models_status = updated_models_status
                    
                    # Cria um mapa de modelos atualizados por nome para reutilizar os mesmos objetos
                    models_map = {ms.name: ms for ms in models_status}
                    
                    # Atualiza models_by_category usando os mesmos objetos atualizados de models_status
                    updated_models_by_category = {}
                    for category, category_models in models_by_category.items():
                        updated_category_models = []
                        for model_status in category_models:
                            # Usa o modelo atualizado de models_status se existir
                            if model_status.name in models_map:
                                updated_category_models.append(models_map[model_status.name])
                            else:
                                # Se não encontrou, cria um modelo com tier unknown
                                updated_model = ModelStatus(
                                    name=model_status.name,
                                    available=model_status.available,
                                    blocked=model_status.blocked,
                                    status=model_status.status,
                                    category=model_status.category,
                                    tier="unknown"
                                )
                                updated_category_models.append(updated_model)
                        updated_models_by_category[category] = updated_category_models
                    
                    models_by_category = updated_models_by_category
                    models_with_tier = sum(1 for m in models_status if m.tier and m.tier != "unknown")
                    logger.info(f"Tiers mesclados com sucesso. {models_with_tier} modelos com tier definido (não-unknown), {len(models_status)} total")
                except Exception as tier_error:
                    logger.error(f"Erro ao detectar tiers: {tier_error}", exc_info=True)
                    # Em caso de erro, marca todos como unknown para garantir que sempre tenha um valor
                    updated_models_status = []
                    for model_status in models_status:
                        updated_model = ModelStatus(
                            name=model_status.name,
                            available=model_status.available,
                            blocked=model_status.blocked,
                            status=model_status.status,
                            category=model_status.category,
                            tier="unknown"
                        )
                        updated_models_status.append(updated_model)
                    models_status = updated_models_status
                    
                    # Atualiza models_by_category também
                    models_map = {ms.name: ms for ms in models_status}
                    updated_models_by_category = {}
                    for category, category_models in models_by_category.items():
                        updated_category_models = [models_map.get(ms.name, ms) for ms in category_models]
                        updated_models_by_category[category] = updated_category_models
                    models_by_category = updated_models_by_category
                
                # Se há modelos disponíveis (validados ou não bloqueados), chave é válida
                has_available = len(available_models) > 0 or len(blocked_models) < len(all_models)
                
                # Debug: verifica se tiers estão presentes
                models_with_tier = [m for m in models_status if m.tier]
                logger.info(f"Retornando {len(models_status)} modelos, {len(models_with_tier)} com tier definido")
                if models_with_tier:
                    logger.info(f"Exemplo de modelo com tier: {models_with_tier[0].name} - {models_with_tier[0].tier}")
                
                return ApiKeyStatus(
                    service=service,
                    is_valid=has_available,
                    models_status=models_status,
                    available_models=available_models if available_models else [m for m in all_models if m not in blocked_models],
                    blocked_models=blocked_models,
                    error=None if has_available else "Nenhum modelo disponível. Verifique suas cotas de API no console do Google Cloud.",
                    models_by_category=models_by_category
                )
            except Exception as gemini_error:
                error_str = str(gemini_error)
                logger.error(f"Erro ao validar Gemini (chave salva): {error_str}")
                
                # Se for erro de autenticação/chave inválida
                if '401' in error_str or '403' in error_str or 'invalid' in error_str.lower() or 'unauthorized' in error_str.lower() or 'permission' in error_str.lower():
                    return ApiKeyStatus(
                        service=service,
                        is_valid=False,
                        models_status=[],
                        available_models=[],
                        blocked_models=[],
                        error="Chave de API inválida ou sem permissão. Verifique se a chave está correta e se tem acesso aos modelos Gemini.",
                        models_by_category=None
                    )
                
                # Outros erros
                return ApiKeyStatus(
                    service=service,
                    is_valid=False,
                    models_status=[],
                    available_models=[],
                    blocked_models=[],
                    error=f"Erro ao validar modelos Gemini: {error_str[:200]}",
                    models_by_category=None
                )
        
        elif service in ["openrouter", "groq", "together"]:
            status_result = await ApiStatusChecker.check_status(service, decrypted_key)
            
            models_status = [
                ModelStatus(
                    name=model.get("name", "unknown"),
                    available=model.get("available", False),
                    blocked=model.get("blocked", False),
                    status=model.get("status", "unknown"),
                    category=model.get("category")
                )
                for model in status_result.get("models_status", [])
            ]
            
            # Detecta tiers dos modelos
            try:
                logger.info(f"Iniciando detecção de tiers para {service}: {len(models_status)} modelos")
                tier_detector = get_tier_detector()
                api_keys_data = [{
                    'service': service,
                    'api_key': decrypted_key,
                    'models': [{'name': ms.name, 'category': ms.category or 'text'} for ms in models_status]
                }]
                tiers = await tier_detector.detect_all_models(str(current_user.id), api_keys_data)
                
                logger.info(f"Tiers detectados para {service}: {len(tiers)} modelos processados")
                if tiers:
                    sample_keys = list(tiers.keys())[:3]
                    logger.info(f"Exemplos de chaves de tier: {sample_keys}")
                    for key in sample_keys:
                        logger.info(f"  {key}: tier={tiers[key].tier}, método={tiers[key].detection_method}")
                
                # Mescla informações de tier criando novos objetos
                updated_models_status = []
                for model_status in models_status:
                    tier_key = f"{service}:{model_status.name}"
                    if tier_key in tiers:
                        tier_info = tiers[tier_key]
                        # Cria novo ModelStatus com tier atualizado
                        updated_model = ModelStatus(
                            name=model_status.name,
                            available=model_status.available,
                            blocked=model_status.blocked,
                            status=model_status.status,
                            category=model_status.category,
                            tier=tier_info.tier,
                            quota_used=tier_info.quota_info.get('remaining_tokens') if tier_info.quota_info else None,
                            quota_limit=tier_info.quota_info.get('limit_tokens') if tier_info.quota_info else None,
                            cost_last_24h=None if tier_info.cost_info else None
                        )
                        updated_models_status.append(updated_model)
                        logger.debug(f"Tier para {model_status.name}: {tier_info.tier} (método: {tier_info.detection_method})")
                    else:
                        # Se não encontrou tier, cria com unknown
                        updated_model = ModelStatus(
                            name=model_status.name,
                            available=model_status.available,
                            blocked=model_status.blocked,
                            status=model_status.status,
                            category=model_status.category,
                            tier="unknown"
                        )
                        updated_models_status.append(updated_model)
                        logger.warning(f"Tier não encontrado para {model_status.name} (chave esperada: {tier_key})")
                
                models_status = updated_models_status
            except Exception as tier_error:
                logger.error(f"Erro ao detectar tiers para {service}: {tier_error}", exc_info=True)
                # Em caso de erro, marca todos como unknown
                updated_models_status = []
                for model_status in models_status:
                    updated_model = ModelStatus(
                        name=model_status.name,
                        available=model_status.available,
                        blocked=model_status.blocked,
                        status=model_status.status,
                        category=model_status.category,
                        tier="unknown"
                    )
                    updated_models_status.append(updated_model)
                models_status = updated_models_status
            
            return ApiKeyStatus(
                service=service,
                is_valid=status_result.get("is_valid", False),
                models_status=models_status,
                available_models=status_result.get("available_models", []),
                blocked_models=status_result.get("blocked_models", []),
                error=status_result.get("error"),
                models_by_category=None
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Serviço '{service}' não suportado"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar status da chave salva: {e}")
        return ApiKeyStatus(
            service=service,
            is_valid=False,
            models_status=[],
            available_models=[],
            blocked_models=[],
            error=f"Erro ao verificar status: {str(e)}",
            models_by_category=None
        )


@router.get("/{service}/model-tiers")
async def get_model_tiers(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna tiers de todos os modelos de um serviço específico
    """
    try:
        api_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.service == service
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=404,
                detail=f"Chave de API para serviço '{service}' não encontrada"
            )
        
        tier_detector = get_tier_detector()
        cached_tiers = tier_detector.get_cached_tiers(str(current_user.id))
        
        if cached_tiers:
            # Filtra apenas modelos do serviço solicitado
            service_tiers = {
                k.replace(f"{service}:", ""): v.to_dict()
                for k, v in cached_tiers.items()
                if k.startswith(f"{service}:")
            }
            return {"service": service, "tiers": service_tiers}
        else:
            return {"service": service, "tiers": {}, "message": "Cache vazio. Execute refresh-tiers primeiro."}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter tiers: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter tiers: {str(e)}")


@router.post("/{service}/refresh-tiers")
async def refresh_model_tiers(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Força refresh do cache de tiers para um serviço específico
    Limpa o cache e força nova detecção
    """
    try:
        api_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.service == service
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=404,
                detail=f"Chave de API para serviço '{service}' não encontrada"
            )
        
        # Limpa cache para forçar refresh
        tier_detector = get_tier_detector()
        tier_detector.clear_cache(str(current_user.id))
        logger.info(f"Cache limpo para usuário {current_user.id}, serviço {service}")
        
        # Obtém status atual dos modelos (isso vai disparar detecção de tier)
        status = await check_saved_api_key_status(service, current_user, db)
        
        return {
            "service": service,
            "message": "Tiers atualizados com sucesso",
            "models_processed": len(status.models_status)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar tiers: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar tiers: {str(e)}")
