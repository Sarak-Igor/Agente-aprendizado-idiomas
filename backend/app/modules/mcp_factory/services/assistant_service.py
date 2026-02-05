import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.modules.agents_factory.services.llm_provider import LLMProvider
from app.modules.mcp_factory.services.tool_service import ToolService

logger = logging.getLogger(__name__)

class AssistantService:
    """
    O Agente Assistente que ajuda o usuário a criar outros agentes.
    Funciona como um arquiteto de soluções MCP.
    """
    
    def __init__(self, db: Session, user_id):
        self.db = db
        self.user_id = user_id
        self.tool_service = ToolService(db)

    def _get_system_prompt(self) -> str:
        tools = self.tool_service.list_tools()
        tools_desc = "\n".join([f"- {t.name}: {t.description} (Categoria: {t.category})" for t in tools])
        
        return f"""
        Você é o 'Arquiteto de Agentes', um assistente especializado em ajudar usuários a criar Agentes Especialistas com ferramentas MCP.
        
        Sua missão é:
        1. Entender o que o usuário quer que o novo agente faça.
        2. Sugerir o 'Prompt Base' ideal para o novo agente.
        3. Recomendar as ferramentas MCP mais adequadas do catálogo abaixo.
        
        Ferramentas MCP Disponíveis:
        {tools_desc}
        
        REGRAS CRÍTICAS:
        - Suas respostas DEVEM ser em formato JSON puro, sem markdown block (```json).
        - Estrutura obrigatória:
        {{
          "text": "Sua resposta natural ao usuário explicando o que fez...",
          "actions": [
             {{ "type": "ADD_NODE", "node": {{ "type": "brain|tool|logic|wait", "label": "Nome", "id": "id-unico-uuid", "position": {{"x": 0, "y": 0}}, "data": {{...}} }} }},
             {{ "type": "CONNECT", "from": "id_origem", "to": "id_destino" }},
             {{ "type": "INSTALL_TOOL", "tool": "mcp-server-nome" }}
          ]
        }}
        - Use IDs curtos e descritivos para novos nós (ex: 'brain-analise', 'tool-web').
        - Se o usuário pedir para conectar a algo existente, use o ID que está no Blueprint atual fornecido abaixo.
        - Tente posicionar os nós de forma organizada (ex: gatilhos à esquerda, cérebro no meio, ferramentas à direita).
        - Sempre responda o campo "text" em Português.
        """

    async def chat_with_assistant(
        self, 
        user_message: str, 
        history: List[Dict[str, str]] = None,
        model_name: str = "google/gemini-2.0-flash-exp:free",
        current_blueprint: Dict[str, Any] = None
    ) -> str:
        """
        Interage com o usuário para planejar o novo agente.
        Permite a escolha do modelo pelo usuário.
        """
        # Busca o serviço baseado no provedor (gemini ou openrouter via llm_provider)
        service_name = "gemini" if "gemini" in model_name.lower() else "openrouter"
        llm = LLMProvider.get_service(self.db, self.user_id, service_name)
        
        if not llm:
            return '{"text": "Erro: Chave de API não configurada para o provedor deste modelo.", "actions": []}'

        system_prompt = self._get_system_prompt()
        
        full_prompt = f"{system_prompt}\n"
        
        if current_blueprint:
            full_prompt += f"ESTADO ATUAL DO BLUEPRINT:\n{json.dumps(current_blueprint, indent=2)}\n\n"
        
        if history:
            for msg in history:
                role = "USER" if msg['role'] == 'user' else "ASSISTANT"
                # Tentamos extrair apenas o texto se o histórico já estiver em JSON
                content = msg['content']
                try:
                    import json
                    loaded = json.loads(content)
                    if isinstance(loaded, dict) and "text" in loaded:
                        content = loaded["text"]
                except:
                    pass
                full_prompt += f"{role}: {content}\n"
        
        full_prompt += f"USER: {user_message}\nASSISTANT:"

        try:
            response = await asyncio.to_thread(
                llm.generate_text,
                prompt=full_prompt,
                max_tokens=2000,
                model_name=model_name
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Erro no chat do assistente: {e}")
            return json.dumps({
                "text": f"Ocorreu um erro ao tentar usar o modelo {model_name}. Por favor, verifique se sua chave de API para o provedor correspondente está configurada corretamente nas configurações globais do sistema.",
                "actions": []
            })

    def generate_agent_blueprint(self, conversation_context: str) -> Dict[str, Any]:
        """
        Analisa a conversa e extrai o blueprint JSON para o novo agente.
        Transforma o desejo do usuário em estrutura técnica (n8n style).
        """
        # Este método seria uma chamada separada para a LLM pedindo o formato JSON.
        # Por enquanto retornamos um placeholder que o frontend usará.
        return {
            "name": "Agente Novo",
            "base_prompt": "Você é um assistente...",
            "selected_tools": []
        }
