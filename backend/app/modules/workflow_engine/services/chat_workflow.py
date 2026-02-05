"""
Workflow de Orquestração de Chat
Gerencia: Geração de Resposta -> Análise de Mensagem -> Persistência -> Feedback
"""
from typing import Optional, Dict, Any
from .base import BaseWorkflow, WorkflowContext
from app.modules.user_intelligence.models.models import ChatSession, UserProfile
import logging

logger = logging.getLogger(__name__)

class ChatWorkflow(BaseWorkflow):
    """
    Orquestra o fluxo de processamento de uma mensagem de chat
    """
    def __init__(self, chat_service, analyzer, normalizer, prompt_provider):
        super().__init__()
        self.chat_service = chat_service
        self.analyzer = analyzer
        self.normalizer = normalizer
        self.prompt_provider = prompt_provider

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Executa o fluxo completo de chat:
        1. Inicialização e Contexto
        2. Normalização (Idiomas)
        3. Geração de Resposta (LLM)
        4. Orquestração de Feedback e Análise
        """
        session = context.get("session")
        user_message_content = context.get("content")
        user_message_type = context.get("content_type", "text")
        transcription = context.get("transcription")
        user_profile = context.get("user_profile")
        
        context.log(f"Iniciando workflow de chat para sessão {session.id}")

        # 1. Normalização (se necessário)
        message_to_analyze = transcription if transcription else user_message_content
        normalized_message = message_to_analyze
        try:
            if session.language != "en":
                context.log(f"Normalizando mensagem do idioma {session.language}...")
                normalized_message = self.normalizer.normalize_for_storage(
                    message_to_analyze, 
                    session.language
                )
        except Exception as e:
            context.log(f"Erro na normalização: {e}")

        # 2. Geração de Contexto e Chamada LLM
        context.log("Preparando contexto da conversa...")
        # (Lógica movida do ChatService)
        # O workflow agora decide como o prompt é montado usando o prompt_provider
        
        # 3. Geração de Resposta
        context.log("Solicitando resposta ao LLM...")
        llm_result = self._generate_llm_response(session, context, user_profile)
        
        # 4. Resultado Final
        result = {
            "response_content": llm_result["content"],
            "feedback_type": llm_result["feedback_type"],
            "normalized_message": normalized_message,
            "session": session,
            "selected_model": llm_result.get("selected_model"),
            "notices": llm_result.get("notices", [])
        }
        
        context.log("Workflow de chat concluído")
        return result

    def _generate_llm_response(self, session, context, user_profile):
        """Lógica interna de geração delegada ao router e provider com suporte a Fallback"""
        db = self.chat_service.db
        from app.modules.user_intelligence.models.models import ChatMessage
        from app.modules.core_llm.services.selector import UniversalModelSelector, SelectionRequest, ModelCapability
        from app.modules.core_llm.services.orchestrator.base import InsufficientBalanceError, QuotaExceededError, LLMError

        # 1. Obter histórico para contexto
        previous_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at).all()
        
        # 2. Seleção de Modelo Dinâmica (per-message)
        # Permite detectar se o saldo acabou DURANTE a sessão e trocar de modelo
        selector = UniversalModelSelector(db)
        from app.modules.core_llm.services.selector.domain import AgentCategory
        request = SelectionRequest(
            user_id=str(session.user_id),
            function_name="chat",
            agent_category=AgentCategory.CHAT,
            required_capabilities=[ModelCapability.TEXT_INPUT]
        )
        
        selection = selector.select_model(request)
        context.set("selector_notices", selection.notices)

        # Tentativa de chamada com Retry em caso de erro de Custo/Cota
        candidates = [selection.selected_model] + selection.alternatives
        last_error = None
        
        for candidate in candidates:
            service = self.chat_service.chat_router.get_service(candidate.provider)
            if not service: continue
            
            try:
                # Constrói contexto final
                conversation_context = self._build_conversation_context(
                    session, previous_messages, context.get("content"), context.get("transcription"), user_profile
                )
                
                # Chamada real
                response_text = service.generate_text(prompt=conversation_context, max_tokens=1000, model_name=candidate.model)
                
                # Se mudamos o modelo em relação ao que está na sessão, atualizamos a sessão
                if session.model_name != candidate.model:
                    session.model_service = candidate.provider
                    session.model_name = candidate.model
                    # db.commit() # Será commitado no final do ChatService.send_message
                
                # Analisar feedback
                feedback_type = self.prompt_provider.analyze_feedback_type(response_text)
                
                return {
                    "content": response_text,
                    "feedback_type": feedback_type,
                    "selected_model": candidate.model,
                    "notices": selection.notices
                }

            except (InsufficientBalanceError, QuotaExceededError) as e:
                logger.warning(f"Falha de Custo/Cota no modelo {candidate.model}: {e}")
                # Registra no CircuitBreaker para o Seletor saber na PRÓXIMA vez
                reason = "insufficient_balance" if isinstance(e, InsufficientBalanceError) else "quota_exceeded"
                selector.availability.circuit_breaker.record_failure(str(candidate.db_model.get("id")), reason=reason)
                
                # Adiciona notice para o usuário
                msg = "Saldo insuficiente" if reason == "insufficient_balance" else "Cota atingida"
                notice = f"Aviso: {msg} no modelo {candidate.model}. Tentando alternativa..."
                if notice not in selection.notices: selection.notices.append(notice)
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Erro ao gerar resposta com {candidate.model}: {e}")
                last_error = e
                continue

        # Se chegou aqui, todos os candidatos falharam
        raise Exception(f"Não foi possível obter resposta da IA após tentar alternativas. Último erro: {last_error}")

    def _build_conversation_context(self, session, previous_messages, current_content, transcription, user_profile):
        """Constrói o prompt final para o LLM"""
        system_prompt = self.prompt_provider.get_system_prompt(session, user_profile)
        
        context_parts = [
            f"INSTRUÇÕES DO SISTEMA:\n{system_prompt}\n",
            "---",
            "CONVERSA:\n"
        ]
        
        # Mensagens recentes (limite de 10)
        recent = previous_messages[-10:] if len(previous_messages) > 10 else previous_messages
        for msg in recent:
            # Pula prompt inicial se for redundante
            if msg.role == "assistant" and len(msg.content) > 200 and "Você é um professor" in msg.content:
                continue
                
            role_map = {"user": "Aluno", "assistant": "Professor"}
            content = msg.transcription if msg.transcription else msg.content
            context_parts.append(f"{role_map.get(msg.role, msg.role)}: {content}")
            
        # Mensagem atual
        current = transcription if transcription else current_content
        context_parts.append(f"Aluno: {current}")
        context_parts.append("Professor:")
        
        return "\n".join(context_parts)

