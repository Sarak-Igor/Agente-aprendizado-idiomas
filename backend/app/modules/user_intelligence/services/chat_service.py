"""
Serviço de chat para aprendizado de idiomas
Gerencia conversas com LLMs configurados como professores de idioma
"""
from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.database import User
from app.modules.user_intelligence.models.models import ChatSession, ChatMessage, UserProfile
from app.modules.user_intelligence.services.chat_router import ChatRouter
from app.modules.core_llm.services.orchestrator.base import LLMService

# Serviços de domínio (serão injetados ou importados de forma dinâmica no futuro)
from app.modules.language_learning.services.language_normalizer import LanguageNormalizer
from app.modules.language_learning.services.message_analyzer import MessageAnalyzer
from app.modules.language_learning.providers.professor import ProfessorPromptProvider

from app.schemas.analysis_schemas import (
    validate_grammar_errors,
    validate_vocabulary_suggestions,
    validate_topics,
    validate_analysis_metadata
)
from app.modules.workflow_engine.services.base import WorkflowContext
from app.modules.workflow_engine.services.chat_workflow import ChatWorkflow
import logging
import threading
import asyncio

logger = logging.getLogger(__name__)


class ChatService:
    """Serviço para gerenciar chat de aprendizado de idiomas"""
    
    def __init__(
        self,
        chat_router: ChatRouter,
        db: Session,
        user_id: Optional[UUID] = None,
        prompt_provider = ProfessorPromptProvider  # Injeta provedor de domínio
    ):
        self.chat_router = chat_router
        self.db = db
        self.user_id = user_id
        self.prompt_provider = prompt_provider
        
        # Inicializa serviços de análise (devem ser genéricos no futuro)
        self.language_normalizer = LanguageNormalizer(db, user_id)
        self.message_analyzer = MessageAnalyzer(chat_router)
    
    def create_session(
        self,
        user_id: str,
        mode: str,
        language: str,
        user_profile: Optional[UserProfile] = None,
        preferred_service: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> ChatSession:
        """Cria nova sessão de chat"""
        from uuid import UUID
        
        # Se modelo preferido foi fornecido, valida e usa
        if preferred_service and preferred_model:
            # Valida que serviço está disponível
            if not self.chat_router.is_service_available(preferred_service):
                raise Exception(f"Serviço {preferred_service} não está disponível")
            
            # Valida modelo (verifica se está na lista de disponíveis)
            # Por enquanto, aceita qualquer modelo - validação será feita no uso
            model_info = {
                'service': preferred_service,
                'model': preferred_model
            }
        else:
            # Seleciona melhor modelo para a sessão
            model_info = self.chat_router.select_best_model(
                mode=mode,
                user_profile=user_profile,
                preferred_service=preferred_service
            )
        
        if not model_info:
            raise Exception("Nenhum modelo LLM disponível")
        
        session = ChatSession(
            user_id=UUID(user_id),
            mode=mode,
            language=language,
            model_service=model_info.get('service'),
            model_name=model_info.get('model'),
            is_active=True
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Cria mensagem inicial do sistema
        initial_message = self._create_initial_message(session, user_profile)
        self.db.add(initial_message)
        self.db.commit()
        
        logger.info(f"Sessão de chat criada: {session.id} (modo: {mode}, idioma: {language}, modelo: {model_info.get('service')}/{model_info.get('model')})")
        return session
    
    def _create_initial_message(
        self,
        session: ChatSession,
        user_profile: Optional[UserProfile]
    ) -> ChatMessage:
        """Cria mensagem inicial baseada no domínio"""
        # Delega ao provedor de domínio
        system_prompt = self.prompt_provider.get_system_prompt(session, user_profile)
        
        message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=system_prompt,
            content_type="text"
        )
        
        return message
    
    def _build_system_prompt(
        self,
        session: ChatSession,
        user_profile: Optional[UserProfile]
    ) -> str:
        """Obtém prompt do sistema através do provedor de domínio"""
        return self.prompt_provider.get_system_prompt(session, user_profile)
    
    def send_message(
        self,
        session_id: str,
        content: str,
        content_type: str = "text",
        transcription: Optional[str] = None
    ) -> ChatMessage:
        """Envia mensagem do usuário e obtém resposta do professor"""
        session = self.db.query(ChatSession).filter(ChatSession.id == UUID(session_id)).first()
        if not session:
            raise Exception("Sessão não encontrada")
        
        if not session.is_active:
            raise Exception("Sessão não está ativa")
        
        # Prepara contexto para o workflow
        context = WorkflowContext()
        context.set("session", session)
        context.set("content", content)
        context.set("content_type", content_type)
        context.set("transcription", transcription)
        
        # Obtém perfil do usuário
        user_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == session.user_id
        ).first()
        context.set("user_profile", user_profile)

        # Executa Workflow (Síncrono por enquanto para manter compatibilidade de API, 
        # mas estruturado internamente)
        workflow = ChatWorkflow(self, self.message_analyzer, self.language_normalizer, self.prompt_provider)
        
        # Como o método original não é async, vamos usar um helper ou rodar de forma síncrona
        # Em um projeto real, send_message deveria ser async
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(workflow.execute(context))
        except RuntimeError:
            result = asyncio.run(workflow.execute(context))

        # Cria mensagem do usuário (Persistência)
        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=content,
            content_type=content_type,
            transcription=transcription
        )
        self.db.add(user_message)
        self.db.flush()
        
        # Cria mensagem do assistente baseada no resultado do workflow
        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=result['response_content'],
            content_type="text",
            feedback_type=result.get('feedback_type')
        )
        self.db.add(assistant_message)
        
        # Atualiza contador de mensagens
        session.message_count += 1
        
        # Atualiza perfil do usuário (já obtido anteriormente)
        if user_profile:
            user_profile.total_chat_messages += 1
        
        self.db.commit()
        self.db.refresh(user_message)
        self.db.refresh(assistant_message)
        
        # Enfileira análise assíncrona em thread separada
        user_level = "beginner"
        if user_profile and user_profile.proficiency_level:
            user_level = user_profile.proficiency_level
        
        self._enqueue_async_analysis(
            user_message.id,
            result.get('normalized_message'),
            session.language,
            user_level
        )
        
        return assistant_message
    
    def _analyze_feedback_type(self, response: str) -> Optional[str]:
        """Obtém tipo de feedback através do provedor de domínio"""
        return self.prompt_provider.analyze_feedback_type(response)
    
    def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Retorna mensagens da sessão"""
        from uuid import UUID
        
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == UUID(session_id)
        ).order_by(ChatMessage.created_at).limit(limit).all()
        
        return messages
    
    def close_session(self, session_id: str):
        """Fecha sessão de chat"""
        from uuid import UUID
        
        session = self.db.query(ChatSession).filter(ChatSession.id == UUID(session_id)).first()
        if session:
            session.is_active = False
            self.db.commit()
    
    def change_session_model(
        self,
        session_id: str,
        service: str,
        model: str
    ) -> ChatSession:
        """Troca modelo da sessão de chat"""
        from uuid import UUID
        
        session = self.db.query(ChatSession).filter(ChatSession.id == UUID(session_id)).first()
        if not session:
            raise ValueError("Sessão não encontrada")
        
        if not session.is_active:
            raise ValueError("Sessão não está ativa")
        
        # Valida que serviço está disponível
        if not self.chat_router.is_service_available(service):
            raise ValueError(f"Serviço {service} não está disponível")
        
        # Valida modelo (verifica se está na lista de disponíveis do serviço)
        # Para Gemini, valida via ModelRouter
        if service == 'gemini':
            if self.chat_router.gemini_service:
                available_models = self.chat_router.gemini_service.model_router.get_available_models()
                if model not in available_models:
                    raise ValueError(f"Modelo {model} não está disponível para Gemini")
        else:
            # Para outros serviços, valida se modelo está na lista de disponíveis
            # Por enquanto, aceita qualquer modelo - validação será feita no uso
            # (pode ser melhorado no futuro com validação mais rigorosa)
            pass
        
        # Atualiza modelo na sessão
        session.model_service = service
        session.model_name = model
        
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Modelo da sessão {session_id} alterado para {service}/{model}")
        return session
    
    def _enqueue_async_analysis(
        self,
        message_id: UUID,
        normalized_message: str,
        language: str,
        user_level: str
    ):
        """
        Enfileira análise assíncrona da mensagem em thread separada
        
        Args:
            message_id: ID da mensagem no banco
            normalized_message: Mensagem normalizada para inglês
            language: Idioma original
            user_level: Nível do usuário
        """
        def analyze_in_background():
            """Executa análise em background"""
            # Cria nova sessão do banco para thread
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                # Realiza análise
                analysis = self.message_analyzer.analyze_message(
                    normalized_message,
                    language,
                    user_level
                )
                
                # Valida dados antes de armazenar
                validated_grammar_errors = validate_grammar_errors(
                    analysis.get("grammar_errors", [])
                )
                validated_vocabulary = validate_vocabulary_suggestions(
                    analysis.get("vocabulary_suggestions", [])
                )
                validated_topics = validate_topics(
                    analysis.get("topics", [])
                )
                validated_metadata = validate_analysis_metadata(
                    analysis.get("analysis_metadata", {})
                )
                
                # Atualiza mensagem no banco
                message = db.query(ChatMessage).filter(
                    ChatMessage.id == message_id
                ).first()
                
                if message:
                    # Salva dados da análise
                    # Listas vazias [] indicam que a análise foi feita mas não encontrou nada
                    # None indica que a análise não foi executada ou falhou
                    message.grammar_errors = validated_grammar_errors  # Pode ser [] ou lista com dados
                    message.vocabulary_suggestions = validated_vocabulary  # Pode ser [] ou lista com dados
                    message.difficulty_score = analysis.get("difficulty_score")
                    message.topics = validated_topics  # Pode ser [] ou lista com dados
                    message.analysis_metadata = validated_metadata
                    
                    db.commit()
                    logger.info(f"Análise assíncrona concluída para mensagem {message_id}")
                else:
                    logger.warning(f"Mensagem {message_id} não encontrada para atualização")
                    
            except Exception as e:
                logger.error(f"Erro na análise assíncrona da mensagem {message_id}: {e}")
                db.rollback()
            finally:
                db.close()
        
        # Inicia thread em background
        thread = threading.Thread(target=analyze_in_background, daemon=True)
        thread.start()
        logger.debug(f"Análise assíncrona enfileirada para mensagem {message_id}")