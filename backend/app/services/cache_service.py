import time
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class CacheService:
    """
    Serviço de cache simples em memória com suporte a TTL (Time To Live).
    Projetado para ser transparente: se falhar ou expirar, a aplicação segue o fluxo normal.
    """
    _instance = None
    _cache: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """Recupera valor do cache se não estiver expirado"""
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        if time.time() > item['expires_at']:
            logger.debug(f"Cache miss (expirado): {key}")
            del self._cache[key]
            return None
            
        logger.debug(f"Cache hit: {key}")
        return item['value']

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Armazena valor no cache com um tempo de vida (padrão 1h)"""
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl_seconds
        }
        logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")

    def delete(self, key: str):
        """Remove uma chave específica"""
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Limpa todo o cache"""
        self._cache.clear()
        logger.info("Cache limpo com sucesso")

# Singleton global
cache_service = CacheService()
