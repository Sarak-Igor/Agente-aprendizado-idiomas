from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from enum import Enum
from datetime import datetime
from app.modules.core_llm.models.models import ModelCatalog

class SelectionStrategy(str, Enum):
    PERFORMANCE = "performance"
    COST_BENEFIT = "cost_benefit"
    SPEED = "speed"
    CHEAPEST = "cheapest"
    FREE = "free"

class AgentCategory(str, Enum):
    GLOBAL = "global"
    CHAT = "chat"
    CODE = "code"
    VISION = "vision"
    VIDEO = "video"
    MULTIMODAL = "multimodal"
    TRANSLATION = "translation"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"
    AUDIO = "audio"
    CREATIVE = "creative"
    STRUCTURED = "structured"
    SMALL_MODEL = "small_model"

class ModelCapability(str, Enum):
    TEXT_INPUT = "text_input"
    IMAGE_INPUT = "image_input"
    AUDIO_INPUT = "audio_input"
    VIDEO_INPUT = "video_input"
    JSON_MODE = "json_mode"
    FUNCTION_CALLING = "function_calling"

class SelectionRequest(BaseModel):
    user_id: str
    function_name: str  # 'chat', 'translation', 'video_analysis'
    agent_category: AgentCategory = AgentCategory.GLOBAL
    required_capabilities: List[ModelCapability] = [ModelCapability.TEXT_INPUT]
    strategy: Optional[SelectionStrategy] = None  # Se None, usa preferência do usuário ou default
    
    # Contexto opcional para decisão (ex: tamanho do input para estimar custo)
    input_token_estimate: int = 0
    max_cost_usd: Optional[float] = None

class ModelCandidate(BaseModel):
    """Representa um modelo candidato com scores calculados para a estratégia atual."""
    model: str  # Nome do serviço/modelo para instanciar (ex: "gemini-1.5-pro")
    provider: str # google, openrouter, etc.
    db_model: Optional[Dict] = None # Dados brutos do catálogo (simplificado para dict para serialização)
    
    # Scores
    elo_score: float = 0
    performance_score: float = 0
    estimated_cost: float = 0
    
    # Status
    is_fallback: bool = False
    circuit_breaker_open: bool = False

class SelectionResult(BaseModel):
    selected_model: ModelCandidate
    alternatives: List[ModelCandidate]
    strategy_used: SelectionStrategy
    decision_log: List[str]  # Explicação da decisão para debug
    notices: List[str] = [] # Avisos para o usuário (ex: "Migrando para free...")
