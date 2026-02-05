import logging
import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.modules.agents_factory.services.agent_storage_service import AgentStorageService
from app.modules.agents_factory.services.agent_db_service import AgentDBService
from app.modules.agents_factory.services.llm_provider import LLMProvider 
from app.modules.mcp_factory.services.runtime_manager import MCPRuntimeManager
from app.modules.mcp_factory.models.models import MCPTool, AgentToolLink
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)

class BlueprintRunner:
    """
    Motor de execução de blueprints de agentes.
    Interpreta o grafo JSON e orquestra a execução passo-a-passo.
    """

    def __init__(self):
        self.storage_service = AgentStorageService()
        self.db_service = AgentDBService()
        self.runtime_manager = MCPRuntimeManager()

    async def run_agent(self, agent_id: str, input_data: Dict[str, Any] = None, db: Session = None, user_id: str = None) -> Dict[str, Any]:
        """
        Carrega o blueprint e inicia a execução a partir do gatilho.
        """
        logger.info(f"Iniciando execução para o agente {agent_id}")
        
        # 1. Carregar Blueprint
        blueprint = self.storage_service.load_blueprint(agent_id)
        if not blueprint:
            raise ValueError(f"Blueprint não encontrado para o agente {agent_id}")

        # 2. Inicializar Contexto de Execução
        execution_context = {
            "agent_id": agent_id,
            "input": input_data or {},
            "memory": {}, # Dados compartilhados entre nós
            "history": [], # Logs da execução
            "db": db, # Sessão do banco para acesso a chaves/LLM
            "user_id": user_id
        }

        # 3. Encontrar Nó Gatilho
        start_node = self._find_start_node(blueprint)
        if not start_node:
            raise ValueError("O blueprint não possui um nó de Gatilho (trigger) válido.")

        # 4. Iniciar Loop de Execução
        try:
            await self._process_node(start_node, blueprint, execution_context)
        except Exception as e:
            logger.error(f"Erro durante execução do agente {agent_id}: {e}")
            execution_context["error"] = str(e)
            
        return execution_context

    def _find_start_node(self, blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Encontra o primeiro nó do tipo 'trigger'."""
        for node in blueprint.get("nodes", []):
            if node.get("type") == "trigger":
                return node
        return None

    async def _process_node(self, node: Dict[str, Any], blueprint: Dict[str, Any], context: Dict[str, Any]):
        """
        Processa um único nó e recursivamente chama os próximos.
        """
        node_id = node.get("id")
        node_type = node.get("type")
        logger.info(f"Processando nó: {node_id} ({node_type})")

        # --- Execução do Nó ---
        output = None
        
        if node_type == "trigger":
            output = await self._execute_trigger(node, context)
        elif node_type == "brain":
            output = await self._execute_brain(node, context)
        elif node_type == "tool":
            output = await self._execute_tool(node, context)
        elif node_type == "logic":
            output = await self._execute_logic(node, context)
        elif node_type == "wait":
            output = await self._execute_wait(node, context)
        else:
            logger.warning(f"Tipo de nó desconhecido: {node_type}")
            output = {"status": "skipped", "reason": "unknown_type"}

        # Armazena resultado no contexto
        context["memory"][node_id] = output
        context["history"].append({
            "node_id": node_id,
            "type": node_type,
            "output": output,
            "timestamp": datetime.now().isoformat()
        })

        # --- Navegação ---
        # Lógica especial para nós de decisão (if/else) pode ir aqui
        
        next_nodes = self._get_next_nodes(node_id, blueprint)
        for next_node in next_nodes:
            # Em um sistema real, poderíamos usar asyncio.gather para execução paralela se o grafo permitir
            await self._process_node(next_node, blueprint, context)

    def _get_next_nodes(self, current_node_id: str, blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca os próximos nós conectados via edges."""
        next_ids = []
        for edge in blueprint.get("edges", []):
            if edge.get("source") == current_node_id:
                next_ids.append(edge.get("target"))
        
        next_nodes = []
        for n_id in next_ids:
            found = next(filter(lambda n: n["id"] == n_id, blueprint.get("nodes", [])), None)
            if found:
                next_nodes.append(found)
        
        return next_nodes

    # --- Executores de Tipos Específicos (Stubs) ---

    async def _execute_trigger(self, node: Dict[str, Any], context: Dict[str, Any]):
        # O trigger geralmente apenas repassa o input inicial
        return context.get("input")

    async def _execute_brain(self, node: Dict[str, Any], context: Dict[str, Any]):
        db = context.get("db")
        user_id = context.get("user_id")
        
        if not db or not user_id:
            return {"error": "Sem contexto de banco ou usuário para chamar LLM"}

        node_data = node.get("data", {})
        prompt_template = node_data.get("prompt", "")
        model_id = node_data.get("model", "openai/gpt-4o")
        
        # Substituição de Variáveis Silmples: {{input}} ou {{node_id.campo}}
        prompt = self._replace_variables(prompt_template, context)

        # Determina serviço de LLM
        service_name = "openrouter"
        if "gemini" in model_id.lower():
            service_name = "gemini"
        
        llm_service = LLMProvider.get_service(db, user_id, service_name)
        if not llm_service:
            # Fallback para OpenRouter se o específico falhar ou tentativa genérica
            llm_service = LLMProvider.get_service(db, user_id, "openrouter")
        
        if not llm_service:
            return {"error": f"Nenhum provedor LLM configurado para modelo {model_id}"}
            
        try:
            response = await asyncio.to_thread(
                llm_service.generate_text,
                prompt=prompt,
                max_tokens=1000,
                model_name=model_id
            )
            return {"response": response, "model": model_id, "provider": service_name}
        except Exception as e:
            logger.error(f"Erro na chamada LLM: {e}")
            return {"error": str(e)}

    async def _execute_tool(self, node: Dict[str, Any], context: Dict[str, Any]):
        db = context.get("db")
        agent_id = context.get("agent_id")
        node_data = node.get("data", {})
        
        tool_id = node_data.get("id") or node_data.get("tool_id")
        if not tool_id:
            return {"error": "Nenhum ID de ferramenta fornecido no nó"}

        # 1. Buscar metadados da ferramenta
        tool = db.query(MCPTool).filter(MCPTool.id == tool_id).first()
        if not tool:
            # Tentar por nome como fallback
            tool = db.query(MCPTool).filter(MCPTool.name == node_data.get("name")).first()
            if not tool:
                return {"error": f"Ferramenta {tool_id} não encontrada no catálogo"}

        # 2. Buscar credenciais do agente para esta ferramenta
        link = db.query(AgentToolLink).filter(
            AgentToolLink.agent_id == agent_id,
            AgentToolLink.tool_id == tool.id
        ).first()
        
        credentials = {}
        if link and link.encrypted_credentials:
            try:
                decrypted = encryption_service.decrypt(link.encrypted_credentials)
                credentials = json.loads(decrypted)
            except Exception as e:
                logger.error(f"Erro ao decifrar credenciais da ferramenta {tool.name}: {e}")

        # 3. Executar via Runtime Manager
        try:
            result = await self.runtime_manager.execute_tool_command(
                runtime=tool.runtime,
                command=tool.command,
                credentials=credentials
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitui {{input}} e {{node_id.output_key}} no texto."""
        # TODO: Usar Jinja2 para uma engine de template real
        
        # Substitui {{input}}
        if isinstance(context.get("input"), str):
            text = text.replace("{{input}}", context["input"])
        elif isinstance(context.get("input"), dict):
            # Se for dict, tenta injetar como JSON ou campo específico
            text = text.replace("{{input}}", json.dumps(context["input"]))

        # Substitui referências a outros nós {{node-id}}
        def replace_match(match):
            key = match.group(1)
            # Busca na memória
            if key in context["memory"]:
                val = context["memory"][key]
                return str(val.get("response") or val.get("output") or val)
            return match.group(0)

        return re.sub(r"\{\{([^}]+)\}\}", replace_match, text)

    async def _execute_logic(self, node: Dict[str, Any], context: Dict[str, Any]):
        # Validação de condição
        condition_template = node.get("data", {}).get("condition", "True")
        
        # Substitui variáveis na condição para avaliação
        condition_str = self._replace_variables(condition_template, context)
        
        # Avaliação segura simplificada
        # TODO: Usar um parser de expressões real
        result = False
        try:
            # Tenta avaliar como booleano básico ou comparação simples
            # CUIDADO: eval é perigoso, mas aqui estamos em um contexto controlado de backend
            # Idealmente usaríamos algo como 'simpleeval'
            result = eval(condition_str, {"__builtins__": None}, {})
        except Exception as e:
            logger.error(f"Erro ao avaliar condição '{condition_str}': {e}")
            result = False
            
        return {"condition": condition_str, "met": bool(result)}

    async def _execute_wait(self, node: Dict[str, Any], context: Dict[str, Any]):
        delay_str = node.get("data", {}).get("delay", "0")
        
        # Converte delay (ex: "5s", "1m") para segundos
        seconds = 0
        if "s" in delay_str:
            seconds = int(delay_str.replace("s", ""))
        elif "m" in delay_str:
            seconds = int(delay_str.replace("m", "")) * 60
        
        if seconds > 0:
            logger.info(f"Aguardando {seconds} segundos...")
            await asyncio.sleep(min(seconds, 60)) # Limite de 1 min para teste
            
        return {"status": "waited", "delay": delay_str}
