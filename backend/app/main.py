from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.logging_config import setup_logging

# Configura logging primeiro
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Importa modelos para garantir que sejam registrados no Base.metadata
from app.models.database import (
    Video, Translation, ApiKey, Job, TokenUsage, User, ModelCatalog, ModelProviderMapping
)
from app.modules.user_intelligence.models.models import UserProfile, ChatSession, ChatMessage

# Importa rotas básicas e de domínio
from app.api.routes import auth, chat, jobs
from app.modules.language_learning.api import video, practice
# Importa rotas modulares do core_llm
from app.modules.core_llm.api import model_catalog_router, usage_router, api_keys_router

Base.metadata.create_all(bind=engine)


import asyncio

async def periodic_catalog_sync():
    """Tarefa de fundo para manter o catálogo atualizado periodicamente usando o novo módulo core_llm"""
    await asyncio.sleep(5)
    
    while True:
        logger.info("Iniciando ciclo de sincronização do catálogo de modelos (Modular core_llm)...")
        try:
            db = SessionLocal()
            try:
                from app.modules.core_llm.services.catalog.catalog_service import ModelCatalogService
                catalog_service = ModelCatalogService()
                stats = catalog_service.sync_catalog(db)
                db.commit()
                logger.info(f"Sincronização modular concluída: {stats.get('created', 0)} novos, {stats.get('updated', 0)} atualizados.")
            except Exception as e:
                logger.error(f"Erro durante a sincronização modular periódica: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro ao abrir conexão para sincronização modular: {e}")
            
        await asyncio.sleep(10800) # 3 horas

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Ativa sincronização em background
    asyncio.create_task(periodic_catalog_sync())
    logger.info("Tarefa de sincronização periódica do core_llm registrada.")
    yield
    logger.info("Encerrando aplicação...")

app = FastAPI(
    title="Video Translation API",
    description="API para tradução de legendas de vídeos do YouTube",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(video.router)
app.include_router(jobs.router)
app.include_router(practice.router)
app.include_router(auth.router)
app.include_router(chat.router)

# Rotas Modulares do core_llm
app.include_router(api_keys_router)
app.include_router(usage_router)
app.include_router(model_catalog_router)


@app.get("/")
async def root():
    return {"message": "Video Translation API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
