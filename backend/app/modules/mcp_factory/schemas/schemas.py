from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class MCPToolResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    category: str
    description: Optional[str]
    runtime: str
    config_schema: Dict[str, Any]
    metadata_json: Optional[Dict[str, Any]]
    is_active: bool

    class Config:
        from_attributes = True

class MCPToolCreate(BaseModel):
    name: str = Field(..., description="Nome único (slug) da ferramenta")
    display_name: str
    category: Optional[str] = "Custom"
    description: Optional[str] = ""
    runtime: str = Field("node", pattern="^(node|python|api)$")
    command: str = Field(..., description="Comando de instalação ou execução")
    config_schema: Optional[Dict[str, Any]] = {}
    metadata_json: Optional[Dict[str, Any]] = {}

class AssistantChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    model_name: Optional[str] = "google/gemini-2.0-flash-exp:free"
    blueprint: Optional[Dict[str, Any]] = None

class AssistantChatResponse(BaseModel):
    response: str

class AgentToolLinkCreate(BaseModel):
    tool_id: UUID
    credentials: Optional[Dict[str, Any]] = {}

class AgentToolLinkResponse(BaseModel):
    id: UUID
    agent_id: UUID
    tool_id: UUID
    is_enabled: bool
    last_verified: Optional[datetime]
    tool: MCPToolResponse

    class Config:
        from_attributes = True
