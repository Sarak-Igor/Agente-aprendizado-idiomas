from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from .agent_storage_service import AgentStorageService

Base = declarative_base()

class LocalMemory(Base):
    __tablename__ = 'memories'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    embedding_id = Column(String, nullable=True) # Referência ao Chroma se usado

class AgentDBService:
    """
    Gerencia conexões SQLite isoladas para cada agente.
    """
    def __init__(self):
        self.storage_service = AgentStorageService()

    def get_db_url(self, agent_id: str) -> str:
        agent_path = self.storage_service.create_agent_structure(agent_id)
        db_path = agent_path / "memory.sqlite"
        return f"sqlite:///{db_path}"

    def init_db(self, agent_id: str):
        """Cria as tabelas no banco SQLite do agente."""
        db_url = self.get_db_url(agent_id)
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        return engine

    def get_session(self, agent_id: str):
        """Retorna uma sessão SQLAlchemy para o banco do agente."""
        engine = self.init_db(agent_id) # Garante que existe e conecta
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
