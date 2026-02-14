from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Agent(Base):
    """
    Define a 'Especialista' - Um agente IA com propósito e configuração específicos.
    """
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # O "chip" ou instrução mestra que define a função do agente
    base_prompt = Column(Text, nullable=False)
    
    # Configuração técnica (modelo, temperatura, etc.)
    configuration = Column(JSON, nullable=False, default={})
    
    # Identificador único para o namespace no banco vetorial
    vector_namespace = Column(String(100), unique=True, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", backref="agents")
    sessions = relationship("AgentSession", back_populates="agent", cascade="all, delete-orphan")


class AgentSession(Base):
    """
    Uma conversa específica com um Agente Especialista.
    Focada em manter a coerência a longo prazo através de resumos e contexto semântico.
    """
    __tablename__ = "agent_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Resumo consolidado da conversa até o momento (para memória de curto/médio prazo)
    summary = Column(Text, nullable=True)
    
    # Métricas da sessão
    message_count = Column(Integer, default=0)
    last_interaction = Column(DateTime(timezone=True), onupdate=func.now())
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    agent = relationship("Agent", back_populates="sessions")
    user = relationship("User", backref="agent_sessions")
    messages = relationship("AgentChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="AgentChatMessage.created_at")
    # Documentos associados à sessão (RAG). Garantir remoção em cascata via ORM/DB.
    documents = relationship(
        "AgentDocument",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class AgentChatMessage(Base):
    """
    Mensagens trocadas dentro de uma sessão de Agente Especialista.
    """
    __tablename__ = "agent_chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Metadados adicionais da mensagem específica do agente
    metadata_json = Column(JSON, nullable=True)  # ex: { "tool_calls": [...], "logic_step": "..." }
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    session = relationship("AgentSession", back_populates="messages")


class AgentDocument(Base):
    """
    Documentos de conhecimento associados a uma sessão de agente para RAG.
    """
    __tablename__ = "agent_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True) # pdf, txt, etc.
    
    status = Column(String(20), default="processing") # processing, indexed, error
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("AgentSession", back_populates="documents")
