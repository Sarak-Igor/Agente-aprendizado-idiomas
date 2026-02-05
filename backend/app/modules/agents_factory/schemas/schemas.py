from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_prompt: str
    configuration: Optional[Dict[str, Any]] = {}

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AgentSessionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    summary: Optional[str] = None
    message_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChatMessageCreate(BaseModel):
    content: str
    model: Optional[str] = None

class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Blueprint(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    settings: Optional[Dict[str, Any]] = {}
    resilience: Optional[Dict[str, Any]] = {}
