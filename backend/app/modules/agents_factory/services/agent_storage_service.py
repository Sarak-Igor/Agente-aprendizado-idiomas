import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class AgentStorageService:
    """
    Serviço responsável pelo isolamento de dados dos agentes.
    Gerencia a criação de diretórios, salvamento de blueprints e configurações.
    """

    def __init__(self, base_storage_path: str = "storage/agents"):
        # Resolve path relative to the running application (backend root)
        self.base_path = Path(os.getcwd()) / base_storage_path
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Garante que o diretório base de storage exista."""
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def get_agent_path(self, agent_id: str) -> Path:
        """Retorna o caminho absoluto para o diretório do agente."""
        return self.base_path / agent_id

    def create_agent_structure(self, agent_id: str) -> Path:
        """
        Cria a estrutura de diretórios para um novo agente.
        Retorna o caminho do diretório do agente.
        """
        agent_path = self.get_agent_path(agent_id)
        
        # Cria diretórios principais
        (agent_path / "logs").mkdir(parents=True, exist_ok=True)
        (agent_path / "data").mkdir(parents=True, exist_ok=True) # Para SQLite/Chroma
        
        return agent_path

    def save_blueprint(self, agent_id: str, blueprint: Dict[str, Any]) -> str:
        """
        Salva o blueprint.json do agente.
        """
        agent_path = self.create_agent_structure(agent_id)
        blueprint_path = agent_path / "blueprint.json"
        
        with open(blueprint_path, 'w', encoding='utf-8') as f:
            json.dump(blueprint, f, indent=4, ensure_ascii=False)
            
        return str(blueprint_path)

    def load_blueprint(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Carrega o blueprint.json do agente.
        """
        blueprint_path = self.get_agent_path(agent_id) / "blueprint.json"
        
        if not blueprint_path.exists():
            return None
            
        with open(blueprint_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_agent(self, agent_id: str):
        """Remove completamente os dados do agente."""
        agent_path = self.get_agent_path(agent_id)
        if agent_path.exists():
            shutil.rmtree(agent_path)

    def list_agents(self):
        """Lista IDs dos agentes que possuem diretório."""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]
