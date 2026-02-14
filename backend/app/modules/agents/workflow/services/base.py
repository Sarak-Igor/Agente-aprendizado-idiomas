"""
Classe base para workflows do sistema
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import uuid
import time

logger = logging.getLogger(__name__)

class WorkflowContext:
    """Contexto compartilhado entre os passos do workflow"""
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.start_time = time.time()
        self.logs: List[str] = []

    def set(self, key: str, value: Any):
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def log(self, message: str):
        elapsed = time.time() - self.start_time
        msg = f"[{elapsed:.3f}s] {message}"
        self.logs.append(msg)
        logger.info(msg)

class BaseWorkflow(ABC):
    """Interface para todos os workflows"""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    @abstractmethod
    async def execute(self, context: WorkflowContext) -> Any:
        """Executa o workflow"""
        pass
