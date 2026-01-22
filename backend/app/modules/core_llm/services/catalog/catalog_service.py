"""
Serviço para gerenciar o catálogo de modelos
Popula e atualiza o catálogo com dados do Chatbot Arena e OpenRouter
"""
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import httpx
import csv
import io
import re

from app.modules.core_llm.models.models import ModelCatalog, ModelProviderMapping
from app.modules.core_llm.services.catalog.arena_service import ChatbotArenaService

logger = logging.getLogger(__name__)

class ModelCatalogService:
    """Serviço para gerenciar o catálogo de modelos de forma agnóstica"""
    
    def __init__(self, arena_service: Optional[ChatbotArenaService] = None, llm_service = None):
        self.arena_service = arena_service or ChatbotArenaService()
        self.llm_service = llm_service
    
    def sync_catalog(self, db: Session) -> Dict[str, int]:
        """Sincroniza catálogo de modelos"""
        logger.info("Iniciando sincronização do catálogo...")
        stats = {"created": 0, "updated": 0, "errors": 0}
        
        # 1. Busca modelos do OpenRouter
        try:
            or_models = self._fetch_openrouter_models()
            for m_data in or_models:
                self._upsert_model(db, m_data, stats)
        except Exception as e:
            logger.error(f"Erro ao sincronizar OpenRouter: {e}")
            stats["errors"] += 1
            
        # 2. Enriquece com Elo do Chatbot Arena
        try:
            arena_data = self.arena_service.fetch_leaderboard(allow_mock_fallback=True)
            if arena_data:
                for a_data in arena_data:
                    self._update_elo(db, a_data, stats)
        except Exception as e:
            logger.error(f"Erro ao sincronizar Arena: {e}")
            stats["errors"] += 1
            
        db.commit()
        return stats

    def _fetch_openrouter_models(self) -> List[Dict]:
        url = "https://openrouter.ai/api/v1/models"
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return resp.json().get("data", [])
        except Exception as e:
            logger.warning(f"Erro OpenRouter API: {e}")
        return []

    def _upsert_model(self, db: Session, data: Dict, stats: Dict):
        m_id = data.get("id")
        if not m_id: return
        
        model = db.query(ModelCatalog).filter(ModelCatalog.aliases.contains([m_id])).first()
        if not model:
            model = ModelCatalog(
                display_name=data.get("name") or m_id,
                aliases=[m_id],
                canonical_name=[self._normalize_key(m_id)],
                is_active=True,
                source="openrouter"
            )
            db.add(model)
            db.flush()
            stats["created"] += 1
        else:
            stats["updated"] += 1
            
        # Mapping
        self._upsert_mapping(db, model.id, "openrouter", m_id, data.get("pricing"))

    def _update_elo(self, db: Session, arena_data: Dict, stats: Dict):
        m_id = arena_data.get("model")
        norm_key = self._normalize_key(m_id)
        
        model = db.query(ModelCatalog).filter(ModelCatalog.canonical_name.contains([norm_key])).first()
        if model:
            model.elo_rating = arena_data.get("elo_rating")
            model.organization = arena_data.get("organization") or model.organization
            stats["updated"] += 1

    def _upsert_mapping(self, db: Session, model_id, provider: str, p_model_id: str, pricing: Optional[Dict]):
        mapping = db.query(ModelProviderMapping).filter(
            and_(ModelProviderMapping.provider == provider, ModelProviderMapping.provider_model_id == p_model_id)
        ).first()
        
        if not mapping:
            mapping = ModelProviderMapping(
                model_id=model_id,
                provider=provider,
                provider_model_id=p_model_id,
                pricing_info=pricing,
                is_available=True,
                last_verified=datetime.now()
            )
            db.add(mapping)
        else:
            mapping.model_id = model_id
            mapping.pricing_info = pricing
            mapping.last_verified = datetime.now()

    def _normalize_key(self, key: str) -> str:
        s = key.lower().split("/")[-1]
        s = re.sub(r"[^a-z0-9]", "-", s)
        return re.sub(r"-+", "-", s).strip("-")
