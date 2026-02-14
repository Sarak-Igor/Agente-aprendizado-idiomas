"""
Serviço para conectar com o Chatbot Arena (LMSYS) e obter rankings de modelos
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Importação opcional do gradio_client
try:
    from gradio_client import Client
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    logger.warning("gradio_client não está instalado. Instale com: pip install gradio-client")


class ChatbotArenaService:
    """Serviço para acessar dados do Chatbot Arena via Gradio Client"""
    
    def __init__(self):
        self.client = None
        self.space_url = "lmsys/chatbot-arena-leaderboard"
        self.max_retries = 3
        self.retry_delay = 2  # segundos
        # Estado da última tentativa (para diagnóstico/status)
        self.last_api_available: bool = False
        self.last_used_mock: bool = True
        self.last_error: Optional[str] = None
    
    def _connect(self, retry_count: int = 0) -> bool:
        """
        Conecta ao Space do Hugging Face com retry automático
        """
        if not GRADIO_AVAILABLE:
            logger.warning("gradio_client não está disponível, não é possível conectar ao Chatbot Arena")
            self.last_api_available = False
            self.last_used_mock = True
            self.last_error = "gradio_client não disponível"
            return False
        
        try:
            if self.client is None:
                logger.info(f"Conectando ao Chatbot Arena: {self.space_url} (tentativa {retry_count + 1}/{self.max_retries})")
                
                # Tenta diferentes métodos de conexão
                connection_methods = [
                    lambda: Client(self.space_url),
                    lambda: Client(f"https://lmsys-chatbot-arena-leaderboard.hf.space"),
                ]
                
                for i, method in enumerate(connection_methods):
                    try:
                        logger.debug(f"Tentando método de conexão {i + 1}")
                        self.client = method()
                        logger.info("Conexão estabelecida com sucesso com o Chatbot Arena")
                        self.last_api_available = True
                        self.last_error = None
                        return True
                    except Exception as e:
                        error_msg = str(e)
                        logger.debug(f"Método {i + 1} falhou: {error_msg}")
                        if i < len(connection_methods) - 1:
                            continue
                        raise
                        
            return True
        except Exception as e:
            self.last_api_available = False
            self.last_error = str(e)
            
            if retry_count < self.max_retries - 1:
                logger.warning(f"Aviso: Não foi possível conectar ao Chatbot Arena (tentativa {retry_count + 1}). Tentando novamente...")
                delay = self.retry_delay * (2 ** retry_count)
                time.sleep(delay)
                return self._connect(retry_count + 1)
            
            logger.warning(f"Aviso: Falha ao sincronizar rankings do Arena após {self.max_retries} tentativas. O sistema usará dados locais/cache.")
            return False
    
    def fetch_leaderboard(self, allow_mock_fallback: bool = False) -> Optional[List[Dict]]:
        """
        Busca o leaderboard do Chatbot Arena usando múltiplas estratégias
        """
        if not self._connect():
            self.last_used_mock = True
            if allow_mock_fallback:
                logger.warning("Não foi possível conectar ao Chatbot Arena, usando dados mockados")
                return self._get_mock_leaderboard()
            return None
        
        try:
            logger.info("Buscando leaderboard do Chatbot Arena...")
            result = None
            
            # Tenta predicts comuns
            common_fn_indices = [0, 1, 2, 5, 10]
            for i in common_fn_indices:
                try:
                    res = self.client.predict(fn_index=i)
                    if res and self._validate_result(res):
                        result = res
                        logger.info(f"Dados obtidos via fn_index {i}")
                        break
                except:
                    continue
            
            if result:
                models_data = self._parse_leaderboard_data(result)
                if models_data:
                    self.last_used_mock = False
                    self.last_api_available = True
                    return models_data
            
            if allow_mock_fallback:
                return self._get_mock_leaderboard()
            return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar leaderboard: {e}")
            if allow_mock_fallback:
                return self._get_mock_leaderboard()
            return None
    
    def _validate_result(self, result) -> bool:
        if result is None: return False
        if isinstance(result, (list, dict, tuple)):
            return len(result) > 0
        if isinstance(result, str):
            return len(result.strip()) > 0
        return False
    
    def _get_mock_leaderboard(self) -> List[Dict]:
        """Dados mockados para fallback"""
        return [
            {"model": "gpt-4o", "display_name": "GPT-4o", "elo_rating": 1285.0, "organization": "OpenAI"},
            {"model": "claude-3-5-sonnet", "display_name": "Claude 3.5 Sonnet", "elo_rating": 1270.0, "organization": "Anthropic"},
            {"model": "gemini-1.5-pro", "display_name": "Gemini 1.5 Pro", "elo_rating": 1260.0, "organization": "Google"},
            {"model": "llama-3-70b", "display_name": "Llama 3 70B", "elo_rating": 1180.0, "organization": "Meta"}
        ]
    
    def _parse_leaderboard_data(self, raw_data) -> List[Dict]:
        models = []
        try:
            if isinstance(raw_data, list):
                if len(raw_data) > 0 and isinstance(raw_data[0], list):
                    headers = raw_data[0]
                    for row in raw_data[1:]:
                        if len(headers) == len(row):
                            data = dict(zip(headers, row))
                            norm = self._normalize_model_data(data)
                            if norm: models.append(norm)
                else:
                    for item in raw_data:
                        norm = self._normalize_model_data(item) if isinstance(item, dict) else None
                        if norm: models.append(norm)
            return models
        except Exception:
            return []
    
    def _normalize_model_data(self, data: Dict) -> Optional[Dict]:
        try:
            model_name = data.get("model") or data.get("Model") or data.get("name")
            if not model_name: return None
            
            return {
                "model": model_name,
                "display_name": data.get("display_name") or model_name,
                "elo_rating": self._safe_float(data.get("elo_rating") or data.get("Elo Rating")),
                "organization": data.get("organization") or data.get("Organization"),
                "license_type": "proprietary" if "proprietary" in str(data.get("license", "")).lower() else "open_source"
            }
        except:
            return None
            
    def _safe_float(self, value) -> Optional[float]:
        if value is None: return None
        try:
            if isinstance(value, (int, float)): return float(value)
            cleaned = ''.join(c for c in str(value) if c.isdigit() or c in '.-')
            return float(cleaned) if cleaned else None
        except: return None
