from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Idioma nativo e idioma aprendido
    native_language = Column(String(10), nullable=False, default="pt")  # pt, en, es, etc.
    learning_language = Column(String(10), nullable=False, default="en")  # Idioma que está aprendendo
    
    # Nível de conhecimento (beginner, intermediate, advanced)
    proficiency_level = Column(String(20), nullable=False, default="beginner")
    
    # Métricas de progresso
    total_chat_messages = Column(Integer, default=0)
    total_practice_sessions = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)  # Tempo médio de resposta em segundos
    
    # Contexto de aprendizado (JSONB para flexibilidade)
    learning_context = Column(JSONB, nullable=True)  # Tópicos estudados, dificuldades, etc.
    
    # Preferências
    preferred_learning_style = Column(String(50), nullable=True)  # formal, casual, conversational
    preferred_model = Column(String(100), nullable=True)  # Modelo preferido do usuário (legacy)
    model_preferences = Column(JSONB, nullable=True)  # { "chat": "performance", "translation": "cost" }
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="profile")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Configuração da sessão
    mode = Column(String(20), nullable=False, default="writing")  # writing, conversation
    language = Column(String(10), nullable=False)  # Idioma sendo praticado
    
    # Modelo usado na sessão
    model_service = Column(String(50), nullable=True)  # gemini, openrouter, groq, together
    model_name = Column(String(100), nullable=True)  # Nome específico do modelo
    
    # Status e métricas
    is_active = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0)
    
    # Contexto da sessão (para continuidade)
    session_context = Column(JSONB, nullable=True)  # Tópicos discutidos, erros comuns, etc.
    
    # Configurações do professor
    teaching_language = Column(String(10), nullable=True)  # Idioma que o professor ensina (padrão: language)
    custom_prompt = Column(Text, nullable=True)  # Prompt personalizado do professor
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Conteúdo
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_type = Column(String(20), nullable=False, default="text")  # text, audio
    
    # Metadados de áudio (se aplicável)
    audio_url = Column(String(500), nullable=True)  # URL do arquivo de áudio
    transcription = Column(Text, nullable=True)  # Transcrição do áudio
    
    # Análise e feedback (para mensagens do usuário)
    grammar_errors = Column(JSONB, nullable=True)  # Lista de erros gramaticais detectados
    vocabulary_suggestions = Column(JSONB, nullable=True)  # Sugestões de vocabulário
    difficulty_score = Column(Float, nullable=True)  # Dificuldade estimada da mensagem
    topics = Column(JSONB, nullable=True)  # Tópicos identificados (em inglês)
    analysis_metadata = Column(JSONB, nullable=True)  # Metadados da análise
    
    # Feedback do professor (para mensagens do assistant)
    feedback_type = Column(String(50), nullable=True)  # correction, explanation, encouragement, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    session = relationship("ChatSession", back_populates="messages")
