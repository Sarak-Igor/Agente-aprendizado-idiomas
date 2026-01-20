"""
Schemas Pydantic para validação de dados de análise
Garante integridade dos dados armazenados em campos JSONB
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class GrammarErrorSchema(BaseModel):
    """Schema para erro gramatical"""
    type: str = Field(..., description="Tipo de erro em inglês (ex: verb_tense, article)")
    original: str = Field(..., description="Texto original com erro")
    corrected: str = Field(..., description="Texto corrigido")
    explanation: Optional[str] = Field(None, description="Explicação do erro")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiança na detecção (0.0 a 1.0)")
    position: Optional[Dict[str, int]] = Field(None, description="Posição do erro no texto {start, end}")


class VocabularySuggestionSchema(BaseModel):
    """Schema para sugestão de vocabulário"""
    word: str = Field(..., description="Palavra em inglês")
    suggestion: Optional[str] = Field(None, description="Sugestão de palavra melhor ou None")
    context: Optional[str] = Field(None, description="Contexto de uso")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$", description="Dificuldade da palavra")
    frequency: Optional[int] = Field(None, ge=0, description="Frequência de uso")


class TopicSchema(BaseModel):
    """Schema para tópico identificado"""
    name: str = Field(..., description="Nome do tópico em inglês")
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Confiança na identificação")
    category: Optional[str] = Field(None, description="Categoria do tópico")


class AnalysisMetadataSchema(BaseModel):
    """Schema para metadados de análise"""
    analyzed_at: str = Field(..., description="Timestamp da análise (ISO format)")
    analyzer_version: str = Field(..., description="Versão do analisador usado")
    confidence_scores: Dict[str, float] = Field(..., description="Scores de confiança por tipo de análise")
    processing_time_ms: float = Field(..., ge=0.0, description="Tempo de processamento em milissegundos")
    original_language: str = Field(..., description="Idioma original da mensagem")
    normalized_language: str = Field("en", description="Idioma normalizado (sempre 'en')")
    model_used: Optional[str] = Field(None, description="Modelo LLM usado para análise")
    error: Optional[str] = Field(None, description="Erro ocorrido durante análise (se houver)")


def validate_grammar_errors(errors: List[Dict]) -> List[Dict]:
    """
    Valida lista de erros gramaticais
    
    Args:
        errors: Lista de dicionários com erros
    
    Returns:
        Lista validada de erros
    """
    if not errors:
        return []
    
    validated = []
    for error in errors:
        try:
            validated_error = GrammarErrorSchema(**error)
            validated.append(validated_error.model_dump(exclude_none=True))
        except Exception as e:
            # Log erro mas continua com outros
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao validar grammar error: {e}. Dados: {error}")
    
    return validated


def validate_vocabulary_suggestions(suggestions: List[Dict]) -> List[Dict]:
    """
    Valida lista de sugestões de vocabulário
    
    Args:
        suggestions: Lista de dicionários com sugestões
    
    Returns:
        Lista validada de sugestões
    """
    if not suggestions:
        return []
    
    validated = []
    for suggestion in suggestions:
        try:
            validated_suggestion = VocabularySuggestionSchema(**suggestion)
            validated.append(validated_suggestion.model_dump(exclude_none=True))
        except Exception as e:
            # Log erro mas continua com outros
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao validar vocabulary suggestion: {e}. Dados: {suggestion}")
    
    return validated


def validate_topics(topics: List[str]) -> List[str]:
    """
    Valida lista de tópicos
    
    Args:
        topics: Lista de strings com tópicos
    
    Returns:
        Lista validada de tópicos (em inglês)
    """
    if not topics:
        return []
    
    validated = []
    for topic in topics:
        if topic and isinstance(topic, str):
            validated.append(topic.strip().lower())
    
    return validated


def validate_analysis_metadata(metadata: Dict) -> Optional[Dict]:
    """
    Valida metadados de análise
    
    Args:
        metadata: Dicionário com metadados
    
    Returns:
        Metadados validados ou None se inválido
    """
    if not metadata:
        return None
    
    try:
        validated_metadata = AnalysisMetadataSchema(**metadata)
        return validated_metadata.model_dump(exclude_none=True)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Erro ao validar analysis metadata: {e}. Dados: {metadata}")
        return None
