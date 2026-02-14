from typing import Dict, Type, Any
from .base import BaseWorkflow

class WorkflowEngine:
    """
    Gerenciador central de workflows.
    Atua como um registry para diferentes processos de negócio.
    """
    def __init__(self):
        self._workflows: Dict[str, Type[BaseWorkflow]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Registra os workflows padrão do sistema"""
        # ChatWorkflow removido
        pass

    def register(self, name: str, workflow_class: Type[BaseWorkflow]):
        """Registra um novo workflow no motor"""
        self._workflows[name] = workflow_class

    def get_workflow(self, name: str) -> Type[BaseWorkflow]:
        """Recupera a classe de um workflow pelo nome"""
        if name not in self._workflows:
            raise ValueError(f"Workflow '{name}' não encontrado no engine.")
        return self._workflows[name]

# Instância única global para o motor de workflows
workflow_engine = WorkflowEngine()
