"""
Serviço de tradução usando a biblioteca deep-translator
Suporta múltiplos backends, padrão Google Translate
"""
import logging
import time
from typing import Dict, Any, Optional
from deep_translator import GoogleTranslator
from .translation_service import TranslationService

logger = logging.getLogger(__name__)


class DeepTranslatorService(TranslationService):
    """
    Implementação usando deep-translator (wrapper para Google Translate e outros)
    
    Requer:
    - biblioteca deep-translator instalada
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        try:
            # Tenta instanciar para ver se a lib está ok
            GoogleTranslator(source='auto', target='en')
            return True
        except Exception as e:
            self.logger.warning(f"DeepTranslator não disponível: {e}")
            return False
    
    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """
        Traduz texto usando DeepTranslator (Google)
        
        Args:
            text: Texto a traduzir
            target_language: Idioma de destino
            source_language: Idioma de origem ('auto' para detectar)
        
        Returns:
            Texto traduzido
        """
        # Limpa códigos de idioma (remove região se necessário, mas Google costuma aceitar)
        # Ex: pt-BR -> pt (deep-translator prefere códigos simples geralmente)
        target = target_language.split('-')[0]
        source = source_language
        if source != 'auto':
            source = source.split('-')[0]
        
        start_time = time.time()
        try:
            translator = GoogleTranslator(source=source, target=target)
            translated = translator.translate(text)
            
            elapsed = time.time() - start_time
            self.logger.info(
                f"Tradução DeepTranslator: {len(text)} → {len(translated)} caracteres "
                f"em {elapsed:.2f}s"
            )
            
            return translated
            
        except Exception as e:
            self.logger.error(f"Erro DeepTranslator: {e}")
            raise Exception(f"Erro ao traduzir com DeepTranslator: {str(e)}")
