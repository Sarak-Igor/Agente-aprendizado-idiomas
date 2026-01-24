import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.modules.agents_factory.services.llm_provider import LLMProvider
from app.modules.agents_factory.services.rag_service import RAGService
from app.modules.agents_factory.services.memory_service import MemoryService
from app.modules.agents_factory.models.models import AgentSession, AgentChatMessage

from app.modules.core_llm.services.orchestrator.base import LLMError, QuotaExceededError, InsufficientBalanceError

logger = logging.getLogger(__name__)

class AgentChatService:
    """
    Orquestrador principal para interações de chat com Agentes Especialistas.
    Garante que a memória e o contexto sejam injetados corretamente.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.memory_service = MemoryService(db)
        self.rag_service = RAGService(db)

    async def process_user_message(
        self, 
        session_id: UUID, 
        user_id: UUID, 
        content: str,
        model_override: Optional[str] = None
    ) -> AgentChatMessage:
        """
        Garante o ciclo completo de uma mensagem:
        1. Persiste a mensagem do usuário.
        2. Recupera contexto (Resumo + Semântica).
        3. Chama a LLM com o contexto injetado.
        4. Persiste a resposta do assistente.
        5. Gatilha atualização de memória em background.
        """
        try:
            session = self.db.query(AgentSession).filter(
                AgentSession.id == session_id,
                AgentSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError("Sessão não encontrada ou acesso negado.")

            agent = session.agent

            # 1. Persiste mensagem do usuário
            user_msg = AgentChatMessage(
                session_id=session_id,
                role="user",
                content=content
            )
            self.db.add(user_msg)
            session.message_count += 1
            self.db.commit()

            # 2. Recupera contexto de Documentos (RAG)
            rag_context = self.rag_service.retrieve_context(session_id, content)

            # 3. Prepara o System Prompt com Injeção de Memória e RAG
            system_prompt = agent.base_prompt
            
            if rag_context:
                system_prompt += f"\n\n### Contexto Extraído de Documentos:\n{rag_context}"

            if session.summary:
                system_prompt += f"\n\n### Memória da Conversa (Resumo):\n{session.summary}"
                
            if session.semantic_context:
                fact_str = ", ".join([f"{k}: {v}" for k, v in session.semantic_context.items()])
                if fact_str:
                    system_prompt += f"\n\n### Fatos Conhecidos:\n{fact_str}"

            # 3. Recupera histórico recente (além do resumo)
            recent_messages = self.db.query(AgentChatMessage).filter(
                AgentChatMessage.session_id == session_id
            ).order_by(AgentChatMessage.created_at.desc()).limit(10).all()
            recent_messages.reverse()

            # 4. Chama a LLM via LLMProvider com Fallback
            model_name = model_override or agent.configuration.get("model", "google/gemini-2.0-flash-exp:free")
            logger.info(f"Iniciando chat - Agente: {agent.name}, Modelo Final: {model_name}")
            
            # Ordem de tentativa: Se for modelo free ou de empresa específica, tentamos o provedor natural primeiro
            providers_to_try = ["openrouter", "gemini"]
            is_free_request = "free" in model_name.lower()
            
            if "gemini" in model_name.lower() and not is_free_request:
                providers_to_try = ["gemini", "openrouter"]
            
            if is_free_request:
                logger.info("Modelo FREE detectado. Prioridade: OpenRouter.")

            response_text = None
            last_exception = None
            actual_model_used = model_name

            for provider_name in providers_to_try:
                llm = LLMProvider.get_service(self.db, user_id, provider_name)
                if not llm:
                    logger.warning(f"Provedor {provider_name} não disponível para este usuário.")
                    continue
                
                # Lista de modelos para este provedor
                models_to_try = [model_name]
                
                # Se for OpenRouter e o modelo falhou ou é free, buscamos alternativas gratuítas NO MESMO provedor
                if provider_name == "openrouter" and is_free_request:
                    try:
                        from app.modules.core_llm.api.status_checker import ApiStatusChecker
                        from app.services.encryption import encryption_service
                        # Pega a chave para listar outros modelos
                        from app.modules.core_llm.models.models import ApiKey
                        key_rec = self.db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.service == "openrouter").first()
                        if key_rec:
                            key = encryption_service.decrypt(key_rec.encrypted_key)
                            status = await ApiStatusChecker.check_status("openrouter", key, strategy="free", db=self.db)
                            if status.get("is_valid"):
                                alt_models = status.get("available_models", [])
                                # Adiciona alternativas que não sejam o atual
                                for alt in alt_models:
                                    if alt not in models_to_try:
                                        models_to_try.append(alt)
                    except Exception as e:
                        logger.warning(f"Erro ao buscar modelos alternativos free no OpenRouter: {e}")

                for current_model in models_to_try:
                    try:
                        # Ajusta o nome do modelo se for Gemini (limpeza de prefixos)
                        api_model_name = current_model
                        if provider_name == "gemini":
                            if "/" in current_model:
                                api_model_name = "gemini-2.0-flash-exp"
                            elif "gemini" not in current_model.lower():
                                api_model_name = "gemini-1.5-flash"
                                
                        logger.info(f"Tentando {provider_name} com o modelo: {api_model_name}")

                        response_text = llm.generate_text(
                            prompt=f"SYSTEM: {system_prompt}\n\n" + 
                                "\n".join([f"{m.role.upper()}: {m.content}" for m in recent_messages]) + 
                                "\nASSISTANT:",
                            max_tokens=2048,
                            model_name=api_model_name
                        )
                        actual_model_used = api_model_name
                        logger.info(f"Sucesso com {provider_name} ({api_model_name}).")
                        break # Sucesso neste provedor!
                    except (QuotaExceededError, InsufficientBalanceError) as e:
                        logger.warning(f"Cota atingida no modelo {api_model_name} ({provider_name}). Tentando próximo modelo...")
                        last_exception = e
                        continue # Tenta o próximo modelo do mesmo provedor
                    except Exception as e:
                        logger.error(f"Erro no modelo {api_model_name} ({provider_name}): {str(e)}")
                        last_exception = e
                        continue

                if response_text:
                    break # Sai do loop de provedores

            if not response_text:
                error_msg = str(last_exception) if last_exception else "Erro desconhecido"
                if "429" in error_msg or "RESOURCE" in error_msg or "QUOTA" in error_msg:
                    raise Exception("🔄 Limite de uso atingido (Rate Limit). Por favor, aguarde cerca de 30-60 segundos e tente novamente. Dica: Adicione uma chave do OpenRouter para ter fallback automático!")
                logger.error(f"Todos os provedores e modelos falharam: {error_msg}")
                raise last_exception or Exception("Nenhum modelo LLM funcional disponível no momento.")

            # 5. Persiste resposta do assistente
            assistant_msg = AgentChatMessage(
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata_json={"model": actual_model_used}
            )
            self.db.add(assistant_msg)
            session.message_count += 1
            self.db.commit()

            # 6. Atualização de Memória (Background simulado)
            if session.message_count % 5 == 0:
                logger.info(f"Limite de mensagens atingido na sessão {session_id}. Resumindo...")
                await self.memory_service.generate_summary(session_id, user_id)

            return assistant_msg

        except Exception as e:
            logger.error(f"Erro processando mensagem: {str(e)}")
            raise
