"""
Rotas para gerenciamento de chaves de API (Agnóstico)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.api.routes.auth import get_current_user
from app.modules.core_llm.models.models import ApiKey
from app.services.encryption import encryption_service
from app.modules.core_llm.api.status_checker import ApiStatusChecker

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
async def check_key(data: ApiKeyCreate):
    """Verifica se uma chave é válida antes de salvar"""
    result = await ApiStatusChecker.check_status(data.service, data.api_key)
    return result
