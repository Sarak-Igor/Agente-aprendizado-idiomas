from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.database import User
from app.modules.mcp_factory.schemas import schemas
from app.modules.mcp_factory.services.tool_service import ToolService
from app.modules.mcp_factory.services.assistant_service import AssistantService
from app.modules.mcp_factory.models.models import MCPTool, AgentToolLink

router = APIRouter(prefix="/mcp", tags=["2 - MCP Factory"])

@router.get("/tools", response_model=List[schemas.MCPToolResponse])
def list_available_tools(category: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista todas as ferramentas MCP disponíveis no catálogo."""
    tool_service = ToolService(db)
    return tool_service.list_tools(category)

@router.post("/tools/seed")
async def seed_mcp_tools(db: Session = Depends(get_db)):
    """Popula o catálogo inicial de ferramentas MCP."""
    tool_service = ToolService(db)
    await tool_service.seed_tools()
    return {"message": "Catálogo de ferramentas MCP populado com sucesso!"}

@router.post("/tools/custom", response_model=schemas.MCPToolResponse)
def register_custom_tool(tool: schemas.MCPToolCreate, db: Session = Depends(get_db)):
    """Registra uma nova ferramenta customizada/manual."""
    service = ToolService(db)
    try:
        return service.register_custom_tool(tool.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
def list_templates():
    """Lista templates de agentes disponíveis."""
    import os
    import json
    from pathlib import Path
    
    # Assume que a CWD (Current Working Directory) é a raiz do backend
    templates_dir = Path(os.getcwd()) / "templates"
    if not templates_dir.exists():
        return []

    templates = []
    for f in templates_dir.iterdir():
        if f.suffix == ".json":
            try:
                with f.open('r', encoding='utf-8') as file:
                    data = json.load(file)
                    templates.append({
                        "id": f.stem, # Nome do arquivo sem extensão
                        "name": data.get("name", "Sem Nome"),
                        "description": data.get("description", "")
                    })
            except:
                continue
    return templates

@router.get("/templates/{template_id}")
def get_template_content(template_id: str):
    """Retorna o conteúdo JSON completo de um template."""
    import os
    import json
    from pathlib import Path
    
    # Assume que a CWD (Current Working Directory) é a raiz do backend
    templates_dir = Path(os.getcwd()) / "templates"
    file_path = templates_dir / f"{template_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler template: {str(e)}")

@router.post("/assistant/chat", response_model=schemas.AssistantChatResponse)
async def chat_with_assistant(
    chat_in: schemas.AssistantChatRequest, 
    db: Session = Depends(get_db)
):
    """Interage com o Agente Assistente para planejar a criação de um novo especialista."""
    # Placeholder: Em produção, usar ID do usuário logado
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    assistant = AssistantService(db, user.id)
    response_text = await assistant.chat_with_assistant(
        chat_in.message, 
        chat_in.history, 
        chat_in.model_name,
        chat_in.blueprint
    )
    return {"response": response_text}

@router.get("/agents/{agent_id}/tools", response_model=List[schemas.AgentToolLinkResponse])
def list_agent_tools(agent_id: UUID, db: Session = Depends(get_db)):
    """Lista as ferramentas MCP vinculadas a um agente específico."""
    links = db.query(AgentToolLink).filter(AgentToolLink.agent_id == agent_id).all()
    return links

@router.post("/agents/{agent_id}/tools", response_model=schemas.AgentToolLinkResponse)
def link_tool_to_agent(
    agent_id: UUID, 
    link_in: schemas.AgentToolLinkCreate, 
    db: Session = Depends(get_db)
):
    """Vincula uma ferramenta MCP a um agente com as credenciais necessárias."""
    from app.services.encryption import encryption_service
    import json
    
    # Verifica se a ferramenta existe
    tool = db.query(MCPTool).filter(MCPTool.id == link_in.tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Ferramenta MCP não encontrada")
        
    # Cifra as credenciais
    encrypted = encryption_service.encrypt(json.dumps(link_in.credentials))
    
    # Cria ou atualiza o link
    existing_link = db.query(AgentToolLink).filter(
        AgentToolLink.agent_id == agent_id,
        AgentToolLink.tool_id == link_in.tool_id
    ).first()
    
    if existing_link:
        existing_link.encrypted_credentials = encrypted
        db_link = existing_link
    else:
        db_link = AgentToolLink(
            agent_id=agent_id,
            tool_id=link_in.tool_id,
            encrypted_credentials=encrypted
        )
        db.add(db_link)
    
    db.commit()
    db.refresh(db_link)
    return db_link
