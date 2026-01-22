"""
Serviço de normalização de idioma
Traduz textos para inglês antes de armazenar e de volta para exibição
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from app.modules.language_learning.services.translation_factory import TranslationServiceFactory
from app.services.encryption import encryption_service
from app.modules.core_llm.models.models import ApiKey
from sqlalchemy.orm import Session
import logging
import hashlib

logger = logging.getLogger(__name__)


# Dicionário de termos técnicos que não precisam tradução ou têm tradução fixa
TECHNICAL_TERMS = {
    "verb_tense": {
        "pt": "tempo verbal",
        "es": "tiempo verbal",
        "fr": "temps verbal",
        "de": "Zeitform",
        "it": "tempo verbale",
        "en": "verb tense"
    },
    "article": {
        "pt": "artigo",
        "es": "artículo",
        "fr": "article",
        "de": "Artikel",
        "it": "articolo",
        "en": "article"
    },
    "preposition": {
        "pt": "preposição",
        "es": "preposición",
        "fr": "préposition",
        "de": "Präposition",
        "it": "preposizione",
        "en": "preposition"
    },
    "pronoun": {
        "pt": "pronome",
        "es": "pronombre",
        "fr": "pronom",
        "de": "Pronomen",
        "it": "pronome",
        "en": "pronoun"
    },
    "conjugation": {
        "pt": "conjugação",
        "es": "conjugación",
        "fr": "conjugaison",
        "de": "Konjugation",
        "it": "coniugazione",
        "en": "conjugation"
    },
    "plural": {
        "pt": "plural",
        "es": "plural",
        "fr": "pluriel",
        "de": "Plural",
        "it": "plurale",
        "en": "plural"
    },
    "singular": {
        "pt": "singular",
        "es": "singular",
        "fr": "singulier",
        "de": "Singular",
        "it": "singolare",
        "en": "singular"
    },
    "word_order": {
        "pt": "ordem das palavras",
        "es": "orden de las palabras",
        "fr": "ordre des mots",
        "de": "Wortstellung",
        "it": "ordine delle parole",
        "en": "word order"
    }
}


class LanguageNormalizer:
    """
    Normaliza textos para inglês antes de armazenar e traduz de volta para exibição
    """
    
    def __init__(self, db: Session, user_id: Optional[UUID] = None):
        """
        Inicializa normalizador de idioma
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário (opcional, para buscar API keys)
        """
        self.db = db
        self.user_id = user_id
        self.cache: Dict[str, Dict[str, Any]] = {}  # Cache em memória
        self.cache_ttl_days = 30
        self.translation_service = None
        
        # Inicializa serviço de tradução com fallback
        self._init_translation_service()
    
    def _init_translation_service(self):
        """Inicializa serviço de tradução com fallback automático"""
        try:
            # Configurações para cada serviço
            configs = {}
            
            # 1. Deep Translator (prioridade - mais rápido)
            # Não precisa de configuração especial
            configs["deeptranslator"] = {}
            
            # 2. Google Translate (fallback)
            configs["googletrans"] = {"delay": 0.3}
            
            # 3. Gemini (fallback final - melhor qualidade)
            if self.user_id:
                try:
                    api_key_record = self.db.query(ApiKey).filter(
                        ApiKey.user_id == self.user_id,
                        ApiKey.service == "gemini"
                    ).first()
                    
                    if api_key_record:
                        decrypted_key = encryption_service.decrypt(api_key_record.encrypted_key)
                        configs["gemini"] = {"api_key": decrypted_key}
                except Exception as e:
                    logger.debug(f"Erro ao obter API key Gemini: {e}")
            
            # Cria serviço com fallback automático
            # Se não houver serviços disponíveis, não lança exceção, apenas define como None
            try:
                self.translation_service = TranslationServiceFactory.create_auto_fallback(
                    preferred_service="deeptranslator",
                    fallback_services=["googletrans", "gemini"] if "gemini" in configs else ["googletrans"],
                    configs=configs
                )
                logger.info("Serviço de tradução inicializado com sucesso")
            except (ValueError, Exception) as e:
                # Se não há serviços disponíveis, continua sem tradução
                logger.warning(f"Nenhum serviço de tradução disponível: {e}. Sistema continuará sem normalização.")
                self.translation_service = None
        except Exception as e:
            logger.warning(f"Erro ao inicializar serviço de tradução: {e}")
            self.translation_service = None
    
    def _get_cache_key(self, text: str, source: str, target: str) -> str:
        """Gera chave de cache para tradução"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{source}:{target}:{text_hash}"
    
    def _get_cached_translation(self, text: str, source: str, target: str) -> Optional[str]:
        """Obtém tradução do cache se válida"""
        if source == target:
            return text
        
        cache_key = self._get_cache_key(text, source, target)
        cached = self.cache.get(cache_key)
        
        if cached:
            # Verifica se cache ainda é válido
            cache_time = cached.get("timestamp")
            if cache_time:
                age = datetime.now() - cache_time
                if age < timedelta(days=self.cache_ttl_days):
                    return cached.get("translation")
                else:
                    # Remove cache expirado
                    del self.cache[cache_key]
        
        return None
    
    def _cache_translation(self, text: str, source: str, target: str, translated: str):
        """Armazena tradução no cache"""
        if source == target:
            return
        
        cache_key = self._get_cache_key(text, source, target)
        self.cache[cache_key] = {
            "translation": translated,
            "timestamp": datetime.now()
        }
    
    def normalize_for_storage(
        self,
        text: str,
        source_language: str
    ) -> str:
        """
        Traduz texto para inglês antes de armazenar
        
        Args:
            text: Texto a normalizar
            source_language: Idioma original (código ISO, ex: 'pt', 'en')
        
        Returns:
            Texto traduzido para inglês
        """
        if not text or not text.strip():
            return text
        
        # Se já está em inglês, retorna como está
        if source_language == "en":
            return text
        
        # Verifica cache primeiro
        cached = self._get_cached_translation(text, source_language, "en")
        if cached:
            return cached
        
        # Verifica dicionário de termos técnicos
        text_lower = text.lower().strip()
        if text_lower in TECHNICAL_TERMS:
            # Termo técnico: retorna versão em inglês
            return TECHNICAL_TERMS[text_lower]["en"]
        
        # Tenta traduzir usando serviço
        if not self.translation_service:
            logger.warning("Serviço de tradução não disponível, retornando texto original")
            return text
        
        try:
            translated = self.translation_service.translate_text(
                text,
                target_language="en",
                source_language=source_language
            )
            
            # Cacheia tradução
            self._cache_translation(text, source_language, "en", translated)
            return translated
        except Exception as e:
            logger.error(f"Erro ao traduzir para inglês: {e}")
            # Em caso de erro, retorna texto original
            return text
    
    def normalize_for_display(
        self,
        text: str,
        target_language: str
    ) -> str:
        """
        Traduz texto de inglês para idioma do usuário
        
        Args:
            text: Texto em inglês
            target_language: Idioma de destino (código ISO)
        
        Returns:
            Texto traduzido para idioma do usuário
        """
        if not text or not text.strip():
            return text
        
        # Se já está no idioma correto, retorna como está
        if target_language == "en":
            return text
        
        # Verifica cache primeiro
        cached = self._get_cached_translation(text, "en", target_language)
        if cached:
            return cached
        
        # Verifica dicionário de termos técnicos
        text_lower = text.lower().strip()
        if text_lower in TECHNICAL_TERMS:
            # Termo técnico: retorna versão traduzida
            return TECHNICAL_TERMS[text_lower].get(target_language, text)
        
        # Tenta traduzir usando serviço
        if not self.translation_service:
            logger.warning("Serviço de tradução não disponível, retornando texto original")
            return text
        
        try:
            translated = self.translation_service.translate_text(
                text,
                target_language=target_language,
                source_language="en"
            )
            
            # Cacheia tradução
            self._cache_translation(text, "en", target_language, translated)
            return translated
        except Exception as e:
            logger.error(f"Erro ao traduzir para {target_language}: {e}")
            # Em caso de erro, retorna texto original
            return text
    
    def normalize_topics(
        self,
        topics: List[str],
        source_language: str
    ) -> List[str]:
        """
        Normaliza lista de tópicos para inglês
        
        Args:
            topics: Lista de tópicos no idioma original
            source_language: Idioma original
        
        Returns:
            Lista de tópicos em inglês
        """
        if not topics:
            return []
        
        normalized = []
        for topic in topics:
            if topic:
                normalized_topic = self.normalize_for_storage(topic, source_language)
                normalized.append(normalized_topic)
        
        return normalized
    
    def normalize_error_types(
        self,
        error_data: Dict,
        source_language: str
    ) -> Dict:
        """
        Normaliza tipos de erro para inglês
        
        Args:
            error_data: Dicionário com dados do erro
            source_language: Idioma original
        
        Returns:
            Dicionário com tipos de erro normalizados para inglês
        """
        if not error_data:
            return error_data
        
        normalized = error_data.copy()
        
        # Normaliza campo 'type' se existir
        if "type" in normalized and normalized["type"]:
            normalized["type"] = self.normalize_for_storage(
                normalized["type"],
                source_language
            )
        
        # Normaliza campo 'explanation' se existir
        if "explanation" in normalized and normalized["explanation"]:
            normalized["explanation"] = self.normalize_for_storage(
                normalized["explanation"],
                source_language
            )
        
        return normalized
