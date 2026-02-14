from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

from app.database import get_db
from app.modules.agents.factory.schemas import schemas
from app.modules.agents.factory.models.models import Agent, AgentSession
from app.modules.agents.factory.services.agent_chat_service import AgentChatService
from app.modules.agents.factory.services.agent_storage_service import AgentStorageService
from app.modules.agents.factory.services.blueprint_runner import BlueprintRunner

router = APIRouter(prefix="/agents", tags=["Agents Factory"])
storage_service = AgentStorageService()
runner_service = BlueprintRunner()

@router.get("/available-models")
async def get_available_models(db: Session = Depends(get_db)):
    """Retorna lista consolidada de modelos baseada nas chaves do usuário"""
    from app.modules.agents.core_llm.models.models import ApiKey
    from app.modules.agents.core_llm.api.status_checker import ApiStatusChecker
    from app.services.encryption import encryption_service
    from app.models.database import User
    
    # Em um sistema real, usaríamos o user do token JWT
    user = db.query(User).first()
    if not user:
        return {"models": []}
        
    keys = db.query(ApiKey).filter(ApiKey.user_id == user.id).all()
    all_models = []
    
    for k in keys:
        try:
            key_val = encryption_service.decrypt(k.encrypted_key)
            status = await ApiStatusChecker.check_status(k.service, key_val, db=db)
            if status.get("is_valid"):
                for m in status.get("models_status", []):
                    all_models.append({
                        "id": m.get("id") or m.get("name"),
                        "name": m.get("name"),
                        "service": k.service,
                        "tier": m.get("tier")
                    })
        except Exception as e:
            logger.warning(f"Erro ao listar modelos para {k.service}: {e}")
            
    return {"models": all_models}

@router.post("/", response_model=schemas.AgentResponse)
def create_agent(agent_in: schemas.AgentCreate, db: Session = Depends(get_db)):
    # Em produção, pegaríamos o user_id do token JWT
    # Para teste, usaremos um placeholder ou o primeiro usuário
    from app.models.database import User
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado para associar o agente.")

    db_agent = Agent(
        user_id=user.id,
        **agent_in.model_dump()
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    # Cria estrutura de diretórios isolada para o agente
    try:
        storage_service.create_agent_structure(str(db_agent.id))
    except Exception as e:
        logger.error(f"Erro ao criar storage para agente {db_agent.id}: {e}")
        # Não falhamos a request, mas logamos o erro. O storage pode ser criado depois ao salvar blueprint.

    return db_agent

@router.get("/", response_model=List[schemas.AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@router.delete("/{agent_id}")
def delete_agent(agent_id: UUID, db: Session = Depends(get_db)):
    """
    Remove um agente e seus dados associados (sessions, mensagens, documentos e storage).
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    try:
        # Remove dados persistidos em storage (diretórios, blueprints, etc.)
        try:
            storage_service.delete_agent(str(agent.id))
        except Exception as e:
            # Logamos mas não impedimos a remoção no banco caso o storage falhe
            logger.warning(f"Falha ao remover storage do agente {agent.id}: {e}")

        # Remove o registro do agente (cascade cuidará das sessions e mensagens)
        db.delete(agent)
        db.commit()
        return {"status": "deleted", "agent_id": str(agent.id)}
    except Exception as e:
        logger.error(f"Erro ao deletar agente {agent_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar agente: {str(e)}")

@router.post("/{agent_id}/blueprint")
def save_agent_blueprint(agent_id: UUID, blueprint: schemas.Blueprint, db: Session = Depends(get_db)):
    """Salva a definição do fluxo (blueprint) no storage do agente."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    try:
        path = storage_service.save_blueprint(str(agent_id), blueprint.model_dump())
        return {"status": "success", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar blueprint: {str(e)}")

@router.get("/{agent_id}/blueprint", response_model=schemas.Blueprint)
def load_agent_blueprint(agent_id: UUID, db: Session = Depends(get_db)):
    """Carrega o blueprint do storage do agente."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    try:
        blueprint = storage_service.load_blueprint(str(agent_id))
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint não encontrado para este agente")
        return blueprint
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar blueprint: {str(e)}")

@router.post("/{agent_id}/run")
async def run_agent_blueprint(agent_id: UUID, input_data: Dict[str, Any] = {}, db: Session = Depends(get_db)):
    """Executa o blueprint do agente (Motor de Execução)."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    try:
        # Executa de forma assíncrona (em produção, isso deveria ir para uma fila como Celery/BullMQ)
        result = await runner_service.run_agent(str(agent_id), input_data, db=db, user_id=str(agent.user_id))
        return {"status": "completed", "result": result}
    except ValueError as ve:
         raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro na execução do agente {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno de execução: {str(e)}")

# --- Endpoints de Sessão e Chat ---

@router.post("/{agent_id}/sessions", response_model=schemas.AgentSessionResponse)
def create_session(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    # Busca sessão ativa recente para evitar "começar do zero" toda vez
    existing_session = db.query(AgentSession).filter(
        AgentSession.agent_id == agent_id,
        AgentSession.user_id == agent.user_id,
        AgentSession.is_active == True
    ).order_by(AgentSession.created_at.desc()).first()
    
    if existing_session:
        return existing_session
    
    session = AgentSession(
        agent_id=agent_id,
        user_id=agent.user_id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.post("/sessions/{session_id}/chat", response_model=schemas.ChatMessageResponse)
async def chat_with_agent(
    session_id: UUID, 
    chat_in: schemas.ChatMessageCreate, 
    db: Session = Depends(get_db)
):
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    chat_service = AgentChatService(db)
    try:
        response_msg = await chat_service.process_user_message(
            session_id=session_id,
            user_id=session.user_id,
            content=chat_in.content,
            model_override=chat_in.model
        )
        return response_msg
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "cota" in error_msg.lower() or "limit" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Limite de cota atingido no provedor de IA. Verifique seu saldo ou chave de API.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/sessions/{session_id}")
async def get_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return {
        "id": session.id,
        "agent_id": session.agent_id,
        "summary": session.summary,
        "message_count": session.message_count,
        "agent": {
            "name": session.agent.name,
            "base_prompt": session.agent.base_prompt
        }
    }

@router.get("/sessions/{session_id}/messages", response_model=List[schemas.ChatMessageResponse])
def get_messages(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return session.messages

from fastapi import UploadFile, File
from app.modules.agents.factory.services.rag_service import RAGService
from app.modules.agents.factory.models.models import AgentDocument
import shutil
import os
# Logger já definido no topo do arquivo

@router.post("/sessions/{session_id}/documents")
async def upload_document(
    session_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # Garante diretório de uploads
    upload_dir = "./uploads/agents"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{str(session_id)}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Cria registro no banco
    db_doc = AgentDocument(
        session_id=session_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file.filename.split(".")[-1],
        status="processing"
    )
    db.add(db_doc)
    db.commit()

    # Indexação no RAG (Síncrona para este MVP/Fase 2)
    rag_service = RAGService(db)
    success = await rag_service.ingest_file(session_id, file_path, session.user_id)
    
    if success:
        db_doc.status = "indexed"
    else:
        db_doc.status = "error"
        db_doc.error_message = "Falha ao processar conteúdo para busca vetorial."
    
    db.commit()
    db.refresh(db_doc)
    
    return {"id": db_doc.id, "status": db_doc.status, "file_name": db_doc.file_name}
