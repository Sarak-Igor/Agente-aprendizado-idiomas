import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from app.modules.agents_factory.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Serviço responsável pela gestão de memória inteligente: Resumos e Extração Semântica.
    """
    
    def __init__(self, db: Session):
        self.db = db

    async def generate_summary(self, session_id: UUID, user_id: UUID) -> str:
        """
        Gera um resumo consolidado das mensagens de uma sessão.
        Utiliza um modelo de performance (custo-benefício) para a tarefa.
        """
        from app.modules.agents_factory.models.models import AgentSession, AgentChatMessage
        
        session = self.db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if not session:
            return ""

        messages = self.db.query(AgentChatMessage).filter(
            AgentChatMessage.session_id == session_id
        ).order_by(AgentChatMessage.created_at).all()

        if len(messages) < 5:  # Evita resumir conversas muito curtas
            return session.summary or ""

        # Prepara o histórico para a LLM
        history_text = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        prompt = f"""
        Abaixo está o histórico de uma conversa entre um usuário e um Agente IA especialista.
        Sua tarefa é criar um resumo conciso e estruturado que capture os pontos principais, 
        decisões tomadas e o estado atual da solicitação do usuário.
        Este resumo será usado como memória para as próximas interações.

        Histórico:
        {history_text}

        Resumo Conexo e Objetivo:
        """

        try:
            # Busca um serviço de LLM via LLMProvider
            llm = LLMProvider.get_service(self.db, user_id, "openrouter") or \
                  LLMProvider.get_service(self.db, user_id, "gemini")
            
            if not llm:
                logger.error("Nenhum serviço LLM disponível para gerar resumo.")
                return session.summary or ""

            # O core_llm usa generate_text
            summary = llm.generate_text(
                prompt=prompt,
                max_tokens=500,
                model_name="google/gemini-2.0-flash-exp:free"
            )
            
            summary = summary.strip()
            session.summary = summary
            self.db.commit()
            return summary
        except Exception as e:
            logger.error(f"Erro ao gerar resumo para a sessão {session_id}: {str(e)}")
            return session.summary or ""
