from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.modules.agents_factory.schemas import schemas
from app.modules.agents_factory.models.models import Agent, AgentSession
from app.modules.agents_factory.services.agent_chat_service import AgentChatService

router = APIRouter(prefix="/agents", tags=["Agents Factory"])

@router.get("/available-models")
async def get_available_models(db: Session = Depends(get_db)):
    """Retorna lista consolidada de modelos baseada nas chaves do usuário"""
    from app.modules.core_llm.models.models import ApiKey
    from app.modules.core_llm.api.status_checker import ApiStatusChecker
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
    return db_agent

@router.get("/", response_model=List[schemas.AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()

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
        "semantic_context": session.semantic_context,
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
from app.modules.agents_factory.services.rag_service import RAGService
from app.modules.agents_factory.models.models import AgentDocument
import shutil
import os

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
