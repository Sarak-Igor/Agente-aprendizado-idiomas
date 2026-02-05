from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class MCPTool(Base):
    """
    Catálogo de ferramentas MCP disponíveis no sistema.
    Baseado no Model Context Protocol para interoperabilidade.
    """
    __tablename__ = "mcp_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Runtime: 'python' (uv) ou 'node' (npx)
    runtime = Column(String(20), nullable=False)
    
    # Comando base de execução (ex: 'mcp-server-github')
    command = Column(String(500), nullable=False)
    
    # JSON Schema que define as chaves de API / Credenciais necessárias
    config_schema = Column(JSON, nullable=False, default={})
    
    # Metadados adicionais (ex: link de documentação, custo)
    metadata_json = Column(JSON, nullable=True, default={})
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AgentToolLink(Base):
    """
    Vínculo entre um Agente (Especialista) e uma Ferramenta MCP.
    Armazena as configurações e credenciais específicas do agente para aquela ferramenta.
    """
    __tablename__ = "agent_tool_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relacionamento com o Agente (do módulo agents_factory)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relacionamento com a Ferramenta MCP
    tool_id = Column(UUID(as_uuid=True), ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Configurações cifradas (ex: API Keys) preenchidas pelo usuário
    encrypted_credentials = Column(Text, nullable=True) # JSON cifrado
    
    # Status da integração
    is_enabled = Column(Boolean, default=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tool = relationship("MCPTool", backref="agent_links")
    # O relacionamento com Agent será facilitado por um backref ou definido aqui se necessário
