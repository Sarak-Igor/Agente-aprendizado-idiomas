import asyncio
import logging
import subprocess
import os
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

class MCPRuntimeManager:
    """
    Gerenciador de execução para servidores MCP.
    Responsável por iniciar, monitorar e finalizar processos de ferramentas.
    Utiliza npx e uv para garantir isolamento de ambiente.
    """
    
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}

    def _prepare_env(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepara variáveis de ambiente com base nas credenciais do usuário."""
        env = os.environ.copy()
        if credentials:
            env.update(credentials)
        return env

    async def execute_tool_command(
        self, 
        runtime: str, 
        command: str, 
        credentials: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Executa um comando de ferramenta MCP e retorna a saída ou status.
        Nota: Para servidores que rodam continuamente (STDIO), a lógica será diferente.
        Esta implementação foca em execução de comando/verificação.
        """
        try:
            env = self._prepare_env(credentials or {})
            
            # Ajusta o comando baseado no runtime se necessário
            full_command = command
            
            logger.info(f"Executando ferramenta MCP ({runtime}): {full_command}")
            
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout.decode().strip(),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": None,
                    "error": stderr.decode().strip()
                }
                
        except Exception as e:
            logger.error(f"Erro ao executar comando MCP: {str(e)}")
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    async def start_stdio_server(
        self, 
        tool_id: str, 
        runtime: str, 
        command: str, 
        credentials: Dict[str, str] = None
    ):
        """
        Inicia um servidor MCP via STDIO para comunicação contínua com a LLM.
        """
        # TODO: Implementar a orquestração de servidores STDIO persistentes
        pass
