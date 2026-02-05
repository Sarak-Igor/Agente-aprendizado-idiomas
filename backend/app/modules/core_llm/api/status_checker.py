"""
Serviço para verificar status e cotas de diferentes APIs
"""
import httpx
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ApiStatusChecker:
    """Verificador de status para provedores de IA de forma agnóstica"""
    
    @staticmethod
    def _categorize_model(model_id: str, display_name: str = "") -> str:
        """Centraliza a lógica de categorização baseada em heurísticas e palavras-chave"""
        combined = (model_id + " " + display_name).lower()
        
        # 1. Raciocínio (Reasoning)
        if any(x in combined for x in ["o1-", "r1", "deepseek-r1", "thinking", "reasoner", "t-lite"]):
            return "reasoning"
        
        # 2. Código
        if any(x in combined for x in ["codex", "coder", "code-", "codellama", "deepseek-coder", "qwen-coder", "starcoder", "wizardcoder", "sql", "phind", "codestral"]):
            return "code"
            
        # 3. Áudio
        if any(x in combined for x in ["whisper", "audio", "speech", "tts", "sonic"]):
            return "audio"
            
        # 4. Imagem (Geração)
        if any(x in combined for x in ["dall-e", "midjourney", "stable-diffusion", "sdxl", "flux", "imagen", "luma"]):
            return "image"
            
        # 5. Vídeo
        if any(x in combined for x in ["video", "runway", "kling", "sora"]):
            return "video"
            
        # 6. Multimodal (Vision/Capabilities) - Prioridade alta depois de casos específicos (audio/image)
        if any(x in combined for x in ["vision", "vl", "multimodal", "omni", "gpt-4o", "gpt-4-turbo", "claude-3-5", "claude-3-opus", "pixtral", "llava", "bakllava", "minicpm"]):
            return "multimodal"
        
        # Gemini (Generic multimodal check if not nano/haiku)
        if "gemini" in combined and "nano" not in combined:
            return "multimodal"

        # 7. Longo Contexto
        if any(x in combined for x in ["128k", "200k", "1m", "2m", "infinity", "long"]):
            return "long_context"
            
        # 8. Tradução
        if any(x in combined for x in ["translate", "nllb", "aya", "seanlp"]):
            return "translation"
            
        # 9. Dados Estruturados
        if any(x in combined for x in ["extract", "sql", "json", "tool-use", "function"]):
            return "structured"
            
        # 10. Criativo / Roleplay
        if any(x in combined for x in ["mythomax", "story", "novel", "roleplay", "dolphin", "hermes", "character", "mytho", "wizard"]):
            return "creative"
            
        # 11. Baixa Latência / Small
        if any(x in combined for x in ["flash", "haiku", "nano", "micro", "mobile", "instant", "8b", "7b", "3b", "1b"]):
            return "small_model"
            
        # 12. Chat/Instrução
        if any(x in combined for x in ["chat", "instruct", "dialogue", "gpt-", "llama", "mistral", "command"]):
            return "chat"
            
        return "text"

    @staticmethod
    async def check_status(service: str, api_key: str, limit: Optional[int] = None, strategy: Optional[str] = None, db: Optional[Session] = None) -> Dict:
        """Verifica se uma chave de API é válida fazendo uma chamada leve"""
        if service == "gemini":
            return await ApiStatusChecker._check_gemini(api_key, limit, strategy, db)
        elif service == "openrouter":
            return await ApiStatusChecker._check_openrouter(api_key, limit, strategy, db)
        elif service == "groq":
            return await ApiStatusChecker._check_groq(api_key, limit, strategy, db)
        elif service == "together":
            return await ApiStatusChecker._check_together(api_key, limit, strategy, db)
        return {"is_valid": False, "error": "Serviço não suportado para validação automática"}

    @staticmethod
    def _get_category_from_db(db: Session, model_id: str, display_name: str = "") -> Optional[str]:
        """Tenta buscar a categoria real no banco de dados com busca mais flexível"""
        from app.modules.core_llm.models.models import ModelCatalog
        from sqlalchemy import or_
        
        # 1. Busca Exata por Alias ou Display Name
        model = db.query(ModelCatalog).filter(
            or_(
                ModelCatalog.aliases.contains([model_id]),
                ModelCatalog.display_name == display_name,
                ModelCatalog.display_name == model_id
            )
        ).first()
        
        if model:
            return model.category
            
        # 2. Busca Parcial (Fuzzy) - tenta encontrar o ID da API dentro dos aliases ou vice-versa
        # Nota: Como aliases é JSONB, busca parcial é mais complexa, mas vamos tentar pelo nome
        short_id = model_id.split("/")[-1] if "/" in model_id else model_id
        
        model = db.query(ModelCatalog).filter(
            or_(
                ModelCatalog.display_name.ilike(f"%{short_id}%"),
                ModelCatalog.display_name.ilike(f"%{display_name}%")
            )
        ).first()
        
        return model.category if model else None

    @staticmethod
    async def _check_gemini(api_key: str, limit: Optional[int] = None, strategy: Optional[str] = None, db: Optional[Session] = None) -> Dict:
        """Verifica chave do Google Gemini"""
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"key": api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    
                    models_status = []
                    available_models = []
                    
                    for m in models:
                        name = m.get("name", "").split("/")[-1]
                        display_name = m.get("displayName", name)
                        
                        # Tenta DB primeiro, depois heurística
                        category = None
                        if db:
                            category = ApiStatusChecker._get_category_from_db(db, name, display_name)
                        
                        if not category:
                            category = ApiStatusChecker._categorize_model(name, display_name)
                        
                        # Gemini AI Studio keys são free tier com limites
                        tier = "free" 
                        
                        available_models.append(name)
                        models_status.append({
                            "name": display_name,
                            "category": category,
                            "tier": tier,
                            "available": True,
                            "blocked": False,
                            "status": "ok"
                        })
                        
                    return {
                        "is_valid": True,
                        "service": "gemini",
                        "available_models": available_models[:limit],
                        "models_status": models_status[:limit]
                    }
                else:
                    return {"is_valid": False, "error": f"Status {resp.status_code}: {resp.text[:200]}", "available_models": [], "models_status": []}
        except Exception as e:
            return {"is_valid": False, "error": str(e), "available_models": [], "models_status": []}

    @staticmethod
    async def _check_openrouter(api_key: str, limit: Optional[int] = None, strategy: Optional[str] = None, db: Optional[Session] = None) -> Dict:
        url = "https://openrouter.ai/api/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    
                    available_models = []
                    models_status = []
                    
                    for m in models:
                        model_id = m.get("id", "")
                        display_name = m.get("name", model_id)
                        pricing = m.get("pricing", {})
                        
                        prompt_price = float(pricing.get("prompt", "0"))
                        completion_price = float(pricing.get("completion", "0"))
                        
                        # Normalização do Selo Free (Ponto 1 do usuário)
                        is_free_by_price = (prompt_price == 0 and completion_price == 0)
                        is_free_by_name = "free" in (model_id + " " + display_name).lower()
                        
                        tier = "free" if is_free_by_price or is_free_by_name else "paid"
                        
                        # Tenta DB primeiro, depois heurística
                        category = None
                        if db:
                            category = ApiStatusChecker._get_category_from_db(db, model_id, display_name)
                        
                        if not category:
                            category = ApiStatusChecker._categorize_model(model_id, display_name)
                        
                        available_models.append(model_id)
                        models_status.append({
                            "id": model_id,
                            "name": display_name,
                            "category": category,
                            "tier": tier,
                            "available": True,
                            "blocked": False,
                            "status": "ok",
                            "input_price": prompt_price,
                            "output_price": completion_price
                        })
                    
                    if strategy == "free":
                        models_status = [m for m in models_status if m["tier"] == "free"]
                        available_models = [m["id"] for m in models_status]

                    credits_available = "0.00"
                    try:
                        user_resp = await client.get("https://openrouter.ai/api/v1/user", headers={"Authorization": f"Bearer {api_key}"})
                        if user_resp.status_code == 200:
                            user_data = user_resp.json().get("data", {})
                            credits_val = user_data.get("credits")
                            if credits_val is not None:
                                credits_available = f"${float(credits_val):.2f}"
                            else:
                                usage = float(user_data.get("total_usage", 0))
                                if usage > 0:
                                    credits_available = f"-${usage:.2f}"
                                else:
                                    credits_available = "0.00"
                    except Exception as e:
                        logger.warning(f"Erro ao buscar créditos OpenRouter: {e}")

                    return {
                        "is_valid": True,
                        "service": "openrouter",
                        "available_models": available_models[:limit],
                        "models_status": models_status[:limit],
                        "credits": credits_available
                    }
                else:
                    return {"is_valid": False, "service": "openrouter", "error": f"Status {resp.status_code}", "available_models": [], "models_status": []}
        except Exception as e:
            return {"is_valid": False, "service": "openrouter", "error": str(e), "available_models": [], "models_status": []}

    @staticmethod
    async def _check_groq(api_key: str, limit: Optional[int] = None, strategy: Optional[str] = None, db: Optional[Session] = None) -> Dict:
        url = "https://api.groq.com/openai/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    
                    available_models = []
                    models_status = []
                    
                    for m in models:
                        model_id = m.get("id", "")
                        
                        # Tenta DB primeiro, depois heurística
                        category = None
                        if db:
                            category = ApiStatusChecker._get_category_from_db(db, model_id)
                        
                        if not category:
                            category = ApiStatusChecker._categorize_model(model_id)
                        
                        available_models.append(model_id)
                        models_status.append({
                            "name": model_id,
                            "category": category,
                            "tier": "free",
                            "available": True,
                            "blocked": False,
                            "status": "ok"
                        })
                    
                    return {
                        "is_valid": True,
                        "service": "groq",
                        "available_models": available_models[:limit],
                        "models_status": models_status[:limit]
                    }
                else:
                    return {"is_valid": False, "service": "groq", "error": f"Status {resp.status_code}", "available_models": [], "models_status": []}
        except Exception as e:
            return {"is_valid": False, "service": "groq", "error": str(e), "available_models": [], "models_status": []}

    @staticmethod
    async def _check_together(api_key: str, limit: Optional[int] = None, strategy: Optional[str] = None, db: Optional[Session] = None) -> Dict:
        url = "https://api.together.xyz/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    data = resp.json()
                    models = data if isinstance(data, list) else data.get("data", [])
                    
                    available_models = []
                    models_status = []
                    
                    for m in models:
                        model_id = m.get("id") or m.get("name", "")
                        display_name = m.get("display_name") or m.get("name", model_id)
                        
                        # Tenta DB primeiro, depois heurística
                        category = None
                        if db:
                            category = ApiStatusChecker._get_category_from_db(db, model_id, display_name)
                        
                        if not category:
                            category = ApiStatusChecker._categorize_model(model_id, display_name)
                        
                        available_models.append(model_id)
                        models_status.append({
                            "name": display_name,
                            "category": category,
                            "tier": "paid",
                            "available": True,
                            "blocked": False,
                            "status": "ok"
                        })
                    
                    return {
                        "is_valid": True,
                        "service": "together",
                        "available_models": available_models[:limit],
                        "models_status": models_status[:limit]
                    }
                else:
                    return {"is_valid": False, "service": "together", "error": f"Status {resp.status_code}", "available_models": [], "models_status": []}
        except Exception as e:
            return {"is_valid": False, "service": "together", "error": str(e), "available_models": [], "models_status": []}
