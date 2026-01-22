import logging
from app.database import SessionLocal
from app.models.database import ModelCatalog
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapeamento manual de aliases para nomes canônicos
# Cada chave é um alias (ou parte dele) e o valor é a lista canônica desejada
SEED_MAP = {
    "gpt-4o": ["gpt-4o", "chatgpt-4o"],
    "gpt-4o-mini": ["gpt-4o-mini"],
    "gpt-4-turbo": ["gpt-4-turbo"],
    "gpt-3.5-turbo": ["gpt-3-5-turbo"],
    "claude-3-5-sonnet": ["claude-3-5-sonnet"],
    "claude-3-opus": ["claude-3-opus"],
    "claude-3-haiku": ["claude-3-haiku"],
    "gemini-1.5-pro": ["gemini-1-5-pro"],
    "gemini-1.5-flash": ["gemini-1-5-flash"],
    "gemini-2.0-flash": ["gemini-2-0-flash"],
    "llama-3.1-405b": ["llama-3-1-405b"],
    "llama-3.1-70b": ["llama-3-1-70b"],
    "llama-3.1-8b": ["llama-3-1-8b"],
    "mistral-large": ["mistral-large"],
    "mixtral-8x7b": ["mixtral-8x7b"]
}

def seed_canonical_names():
    db = SessionLocal()
    try:
        models = db.query(ModelCatalog).all()
        updated_count = 0
        
        for model in models:
            # Pula se já tiver canonical_name (a menos que seja [])
            if model.canonical_name and len(model.canonical_name) > 0:
                continue
                
            # Tenta encontrar um match no SEED_MAP baseado nos aliases existentes
            matched_canonical = None
            for alias in model.aliases:
                alias_lower = alias.lower()
                for key, canonical_list in SEED_MAP.items():
                    if key in alias_lower:
                        matched_canonical = canonical_list
                        break
                if matched_canonical:
                    break
            
            if matched_canonical:
                logger.info(f"Seeding {model.display_name}: {matched_canonical}")
                model.canonical_name = matched_canonical
                model.last_updated = datetime.now()
                updated_count += 1
        
        db.commit()
        logger.info(f"Seeding concluído: {updated_count} modelos atualizados.")
        
    except Exception as e:
        logger.error(f"Erro no seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_canonical_names()
