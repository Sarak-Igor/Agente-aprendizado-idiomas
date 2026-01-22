"""
Serviço de análise de mensagens do usuário
Extrai erros gramaticais, vocabulário, dificuldade e tópicos usando LLM
"""
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID
from app.modules.user_intelligence.services.chat_router import ChatRouter
from app.modules.core_llm.services.orchestrator.base import LLMService
import json
import logging
import time

logger = logging.getLogger(__name__)

# Versão do analisador
ANALYZER_VERSION = "1.0.0"


class MessageAnalyzer:
    """
    Analisa mensagens do usuário para extrair informações de aprendizado
    """
    
    def __init__(self, chat_router: ChatRouter):
        """
        Inicializa analisador de mensagens
        
        Args:
            chat_router: Roteador de chat com serviços LLM disponíveis
        """
        self.chat_router = chat_router
    
    def analyze_message(
        self,
        message: str,
        language: str,
        user_level: str = "beginner"
    ) -> Dict:
        """
        Analisa mensagem e retorna análise estruturada (tudo em inglês)
        
        Args:
            message: Mensagem já normalizada para inglês
            language: Idioma original da mensagem (para contexto)
            user_level: Nível do usuário (beginner, intermediate, advanced)
        
        Returns:
            Dicionário com análise completa em inglês:
            - grammar_errors: Lista de erros gramaticais
            - vocabulary_suggestions: Sugestões de vocabulário
            - difficulty_score: Score de dificuldade (0.0 a 1.0)
            - topics: Lista de tópicos identificados
        """
        if not message or not message.strip():
            return self._empty_analysis()
        
        start_time = time.time()
        
        try:
            # Obtém serviço LLM disponível
            service = self._get_available_service()
            if not service:
                logger.warning("Nenhum serviço LLM disponível para análise")
                return self._empty_analysis()
            
            # Constrói prompt para análise
            prompt = self._build_analysis_prompt(message, language, user_level)
            
            # Gera análise usando LLM
            response_text = service.generate_text(prompt, max_tokens=2000)
            
            # Parse da resposta JSON
            analysis = self._parse_analysis_response(response_text)
            
            # Calcula tempo de processamento
            processing_time = (time.time() - start_time) * 1000  # em milissegundos
            
            # Adiciona metadados
            analysis["analysis_metadata"] = self._build_analysis_metadata(
                processing_time,
                language
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro ao analisar mensagem: {e}")
            processing_time = (time.time() - start_time) * 1000
            return self._empty_analysis_with_metadata(processing_time, language, str(e))
    
    def analyze_message_async(
        self,
        message_id: UUID,
        message: str,
        language: str,
        user_level: str,
        db_session,
        update_callback
    ) -> None:
        """
        Analisa mensagem de forma assíncrona (background job)
        
        Args:
            message_id: ID da mensagem no banco
            message: Mensagem já normalizada para inglês
            language: Idioma original
            user_level: Nível do usuário
            db_session: Sessão do banco de dados
            update_callback: Função para atualizar mensagem no banco
        """
        try:
            # Realiza análise
            analysis = self.analyze_message(message, language, user_level)
            
            # Atualiza mensagem no banco
            update_callback(
                db_session,
                message_id,
                analysis.get("grammar_errors"),
                analysis.get("vocabulary_suggestions"),
                analysis.get("difficulty_score"),
                analysis.get("topics"),
                analysis.get("analysis_metadata")
            )
            
            logger.info(f"Análise assíncrona concluída para mensagem {message_id}")
            
        except Exception as e:
            logger.error(f"Erro na análise assíncrona da mensagem {message_id}: {e}")
    
    def _get_available_service(self) -> Optional[LLMService]:
        """Obtém primeiro serviço LLM disponível"""
        # Prioridade: Gemini > OpenRouter > Groq > Together
        priority = ['gemini', 'openrouter', 'groq', 'together']
        
        for service_name in priority:
            service = self.chat_router.get_service(service_name)
            if service and service.is_available():
                return service
        
        return None
    
    def _build_analysis_prompt(
        self,
        message: str,
        language: str,
        user_level: str
    ) -> str:
        """Constrói prompt estruturado para análise"""
        return f"""Analyze the following message written by a language learner. The message is already in English (translated from {language}). The learner's level is {user_level}.

Message: "{message}"

Provide a detailed analysis in JSON format with the following structure:
{{
    "grammar_errors": [
        {{
            "type": "error_type_in_english",
            "original": "incorrect_text",
            "corrected": "correct_text",
            "explanation": "brief_explanation_in_english",
            "confidence": 0.95
        }}
    ],
    "vocabulary_suggestions": [
        {{
            "word": "word_in_english",
            "suggestion": "better_alternative_or_none",
            "context": "context_of_usage",
            "difficulty": "easy|medium|hard"
        }}
    ],
    "difficulty_score": 0.65,
    "topics": ["topic1", "topic2"]
}}

Guidelines:
- grammar_errors: List all grammatical errors found. Error types should be in English (e.g., "verb_tense", "article", "preposition", "word_order", "conjugation", "plural", "singular").
- vocabulary_suggestions: List important vocabulary words used. If a word could be improved, provide a suggestion. Otherwise, set suggestion to null.
- difficulty_score: Score from 0.0 (very easy) to 1.0 (very difficult) based on vocabulary complexity, sentence structure, and grammar usage.
- topics: List main topics discussed (in English, e.g., "food", "travel", "greetings", "work", "hobbies").

Return ONLY valid JSON, no additional text."""

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse da resposta JSON do LLM"""
        try:
            # Remove markdown code blocks se presentes
            text = response_text.strip()
            if text.startswith("```"):
                # Remove primeiro e último linha (markdown)
                lines = text.split("\n")
                if len(lines) > 2:
                    text = "\n".join(lines[1:-1])
                else:
                    # Tenta remover apenas ```json e ```
                    text = text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            analysis = json.loads(text)
            
            # Valida e normaliza estrutura
            return self._normalize_analysis(analysis)
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}. Resposta: {response_text[:200]}")
            return self._empty_analysis()
        except Exception as e:
            logger.error(f"Erro ao processar análise: {e}")
            return self._empty_analysis()
    
    def _normalize_analysis(self, analysis: Dict) -> Dict:
        """Normaliza e valida estrutura de análise"""
        normalized = {
            "grammar_errors": [],
            "vocabulary_suggestions": [],
            "difficulty_score": 0.5,
            "topics": []
        }
        
        # Normaliza grammar_errors
        if "grammar_errors" in analysis and isinstance(analysis["grammar_errors"], list):
            for error in analysis["grammar_errors"]:
                if isinstance(error, dict):
                    normalized_error = {
                        "type": error.get("type", "unknown"),
                        "original": error.get("original", ""),
                        "corrected": error.get("corrected", ""),
                        "explanation": error.get("explanation"),
                        "confidence": max(0.0, min(1.0, error.get("confidence", 0.9)))
                    }
                    normalized["grammar_errors"].append(normalized_error)
        
        # Normaliza vocabulary_suggestions
        if "vocabulary_suggestions" in analysis and isinstance(analysis["vocabulary_suggestions"], list):
            for vocab in analysis["vocabulary_suggestions"]:
                if isinstance(vocab, dict):
                    normalized_vocab = {
                        "word": vocab.get("word", ""),
                        "suggestion": vocab.get("suggestion"),
                        "context": vocab.get("context"),
                        "difficulty": vocab.get("difficulty", "medium")
                    }
                    # Valida difficulty
                    if normalized_vocab["difficulty"] not in ["easy", "medium", "hard"]:
                        normalized_vocab["difficulty"] = "medium"
                    normalized["vocabulary_suggestions"].append(normalized_vocab)
        
        # Normaliza difficulty_score
        if "difficulty_score" in analysis:
            try:
                score = float(analysis["difficulty_score"])
                normalized["difficulty_score"] = max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                normalized["difficulty_score"] = 0.5
        
        # Normaliza topics
        if "topics" in analysis and isinstance(analysis["topics"], list):
            for topic in analysis["topics"]:
                if topic and isinstance(topic, str):
                    normalized["topics"].append(topic.strip().lower())
        
        return normalized
    
    def _build_analysis_metadata(
        self,
        processing_time_ms: float,
        original_language: str
    ) -> Dict:
        """Constrói metadados da análise"""
        return {
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "analyzer_version": ANALYZER_VERSION,
            "confidence_scores": {
                "grammar_errors": 0.9,
                "vocabulary": 0.85,
                "difficulty": 0.8,
                "topics": 0.85
            },
            "processing_time_ms": round(processing_time_ms, 2),
            "original_language": original_language,
            "normalized_language": "en"
        }
    
    def _empty_analysis(self) -> Dict:
        """Retorna análise vazia"""
        return {
            "grammar_errors": [],
            "vocabulary_suggestions": [],
            "difficulty_score": 0.5,
            "topics": [],
            "analysis_metadata": None
        }
    
    def _empty_analysis_with_metadata(
        self,
        processing_time_ms: float,
        original_language: str,
        error: Optional[str] = None
    ) -> Dict:
        """Retorna análise vazia com metadados"""
        metadata = self._build_analysis_metadata(processing_time_ms, original_language)
        if error:
            metadata["error"] = error
        
        return {
            "grammar_errors": [],
            "vocabulary_suggestions": [],
            "difficulty_score": 0.5,
            "topics": [],
            "analysis_metadata": metadata
        }
