"""
Serviço para verificar status e cotas de diferentes APIs
"""
import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ApiStatusChecker:
    """Verificador de status para provedores de IA de forma agnóstica"""
    
    @staticmethod
    async def check_status(service: str, api_key: str) -> Dict:
        """Verifica se uma chave de API é válida fazendo uma chamada leve"""
        if service == "openrouter":
            return await ApiStatusChecker._check_openrouter(api_key)
        elif service == "groq":
            return await ApiStatusChecker._check_groq(api_key)
        return {"is_valid": False, "error": "Serviço não suportado para validação automática"}

    @staticmethod
    async def _check_openrouter(api_key: str) -> Dict:
        url = "https://openrouter.ai/api/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                return {"is_valid": resp.status_code == 200}
        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    @staticmethod
    async def _check_groq(api_key: str) -> Dict:
        url = "https://api.groq.com/openai/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                return {"is_valid": resp.status_code == 200}
        except Exception as e:
            return {"is_valid": False, "error": str(e)}
