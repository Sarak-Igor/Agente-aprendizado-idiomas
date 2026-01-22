"""
Rotas para consulta de uso de tokens (Agnóstico)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.api.routes.auth import get_current_user
from app.modules.core_llm.services.usage.token_usage_service import TokenUsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])

@router.get("/stats")
async def get_stats(
    days: int = 30,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém estatísticas de uso do usuário logado"""
    service = TokenUsageService(db)
    stats = service.get_usage_stats(user_id=current_user.id, days=min(days, 365))
    return stats
