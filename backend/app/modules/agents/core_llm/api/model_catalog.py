"""
Rotas para gerenciar o catálogo de modelos (Agnóstico)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.api.routes.auth import get_current_user
from app.modules.agents.core_llm.models.models import ModelCatalog, ModelProviderMapping
from app.modules.agents.core_llm.services.catalog.catalog_service import ModelCatalogService

router = APIRouter(prefix="/api/model-catalog", tags=["model-catalog"])
logger = logging.getLogger(__name__)

class CatalogStatusResponse(BaseModel):
    is_populated: bool
    total_models: int
    last_updated: Optional[datetime]
    source: Optional[str]
    api_available: bool

@router.get("/status", response_model=CatalogStatusResponse)
async def get_catalog_status(db: Session = Depends(get_db)):
    """Retorna o status do catálogo de modelos"""
    try:
        total_models = db.query(func.count(ModelCatalog.id)).filter(ModelCatalog.is_active == True).scalar() or 0
        last_model = db.query(ModelCatalog).filter(ModelCatalog.is_active == True).order_by(ModelCatalog.last_updated.desc()).first()
        
        return CatalogStatusResponse(
            is_populated=total_models > 0,
            total_models=total_models,
            last_updated=last_model.last_updated if last_model else None,
            source=last_model.source if last_model else None,
            api_available=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync")
async def sync_catalog(db: Session = Depends(get_db)):
    """Sincroniza o catálogo com as fontes externas"""
    service = ModelCatalogService()
    stats = service.sync_catalog(db)
    return {"success": True, "stats": stats}

@router.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """Lista modelos ativos e seus provedores"""
    models = db.query(ModelCatalog).filter(ModelCatalog.is_active == True).all()
    result = []
    for m in models:
        mappings = db.query(ModelProviderMapping).filter(ModelProviderMapping.model_id == m.id).all()
        result.append({
            "id": str(m.id),
            "display_name": m.display_name,
            "elo_rating": m.elo_rating,
            "category": m.category,
            "mappings": [{"provider": x.provider, "model_id": x.provider_model_id} for x in mappings]
        })
    return {"total": len(result), "models": result}
