"""
Rotas para gerenciamento de chaves de API (Agnóstico)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.api.routes.auth import get_current_user
from app.modules.agents.core_llm.models.models import ApiKey
from app.services.encryption import encryption_service
from app.modules.agents.core_llm.api.status_checker import ApiStatusChecker

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

class ApiKeyCreate(BaseModel):
    service: str
    api_key: str

@router.post("/")
async def save_key(data: ApiKeyCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Salva ou atualiza uma chave de API criptografada"""
    encrypted = encryption_service.encrypt(data.api_key)
    key = db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.service == data.service).first()
    
    if key:
        key.encrypted_key = encrypted
    else:
        key = ApiKey(user_id=current_user.id, service=data.service, encrypted_key=encrypted)
        db.add(key)
    
    db.commit()
    return {"success": True, "service": data.service}

@router.get("/list")
async def list_keys(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista serviços com chaves cadastradas"""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return {"api_keys": [{"service": k.service, "id": str(k.id)} for k in keys]}

@router.post("/check")
async def check_key(data: ApiKeyCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verifica se uma chave é válida antes de salvar"""
    # Forçamos limit=None para trazer todos os modelos, ignorando qualquer preferência de limite
    limit = None 
    strategy = None
    if current_user and hasattr(current_user, 'profile') and current_user.profile:
        prefs = current_user.profile.model_preferences or {}
        # Ignoramos model_list_limit para garantir a lista completa
        strategy = prefs.get("global_strategy") or prefs.get("chat")
        
    result = await ApiStatusChecker.check_status(data.service, data.api_key, limit=limit, strategy=strategy, db=db)
    return result

@router.post("/check/{service}/saved")
async def check_saved_key(service: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verifica status de uma chave já salva no banco"""
    key = db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.service == service).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="Chave não encontrada para este serviço")
    
    decrypted_key = encryption_service.decrypt(key.encrypted_key)
    
    # Forçamos limit=None para trazer todos os modelos
    limit = None
    strategy = None
    if current_user and hasattr(current_user, 'profile') and current_user.profile:
        prefs = current_user.profile.model_preferences or {}
        # Ignoramos model_list_limit para garantir a lista completa
        strategy = prefs.get("global_strategy") or prefs.get("chat")
        
    result = await ApiStatusChecker.check_status(service, decrypted_key, limit=limit, strategy=strategy, db=db)
    return result

@router.delete("/{key_id}")
async def delete_key(key_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deleta uma chave pelo ID"""
    from uuid import UUID
    key = db.query(ApiKey).filter(ApiKey.id == UUID(key_id), ApiKey.user_id == current_user.id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Chave não encontrada")
    db.delete(key)
    db.commit()
    return {"success": True}

@router.delete("/service/{service}")
async def delete_by_service(service: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deleta uma chave pelo serviço"""
    key = db.query(ApiKey).filter(ApiKey.user_id == current_user.id, ApiKey.service == service).first()
    if not key:
        raise HTTPException(status_code=404, detail="Chave não encontrada")
    db.delete(key)
    db.commit()
    return {"success": True}
