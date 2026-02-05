from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Text, Boolean, Float
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    youtube_id = Column(String(20), nullable=False, index=True)
    title = Column(String(500))
    duration = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="videos")
    translations = relationship("Translation", back_populates="video", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="video")  # Removido cascade - chaves são do usuário, não do vídeo
    
    __table_args__ = (
        UniqueConstraint('user_id', 'youtube_id', name='unique_user_video'),
    )


class Translation(Base):
    __tablename__ = "translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    segments = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="translations")
    video = relationship("Video", back_populates="translations")
    
    __table_args__ = (
        UniqueConstraint('video_id', 'source_language', 'target_language', name='unique_video_translation'),
    )


from app.modules.core_llm.models.models import ApiKey, TokenUsage


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(20), nullable=False, default="queued")  # queued, processing, completed, error
    progress = Column(Integer, default=0)
    message = Column(String(500))
    error = Column(Text)
    translation_service = Column(String(50))  # Nome do serviço de tradução usado (gemini, googletrans, argos, etc)
    # Campos para checkpoint e retomada
    last_translated_group_index = Column(Integer, default=-1)  # Índice do último grupo traduzido
    partial_segments = Column(JSONB, nullable=True)  # Segmentos parcialmente traduzidos
    blocked_models = Column(JSONB, nullable=True)  # Lista de modelos bloqueados por cota
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", backref="jobs")


# TokenUsage migrado


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    # Relações reversas definidas nos outros modelos (videos, translations, api_keys, jobs, token_usage)


from app.modules.user_intelligence.models.models import UserProfile, ChatSession, ChatMessage
from app.modules.core_llm.models.models import ModelCatalog, ModelProviderMapping
from app.modules.agents_factory.models.models import Agent, AgentSession, AgentChatMessage, AgentDocument
from app.modules.mcp_factory.models.models import MCPTool, AgentToolLink
