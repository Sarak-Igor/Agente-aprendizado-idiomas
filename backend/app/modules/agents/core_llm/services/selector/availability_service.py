
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class ModelCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_sec: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_sec)
        
        # Estado em memória: { model_id_str: { failures: int, last_failure: datetime, state: str } }
        self._registry: Dict[str, Dict] = {}

    def is_available(self, model_id: str) -> bool:
        """Verifica se o modelo está disponível (CLOSED ou HALF-OPEN test)."""
        state = self._get_state(model_id)
        
        if state['state'] == CircuitBreakerState.CLOSED:
            return True
            
        if state['state'] == CircuitBreakerState.OPEN:
            # Check timeout
            if datetime.now() - state['last_failure'] > self.recovery_timeout:
                logger.info(f"CircuitBreaker para {model_id} mudou para HALF-OPEN (Recovery Test).")
                state['state'] = CircuitBreakerState.HALF_OPEN
                return True # Permite 1 request para teste
            return False
            
        if state['state'] == CircuitBreakerState.HALF_OPEN:
            # Já tem alguém testando? Poderíamos bloquear concorrentes, 
            # mas simplificando: permite uso. Se falhar, volta pra open.
            return True
            
        return True

    def record_success(self, model_id: str):
        """Registra sucesso na chamada. Reseta falhas."""
        if model_id in self._registry:
            logger.info(f"CircuitBreaker para {model_id} recuperado/resetado.")
            del self._registry[model_id]

    def record_failure(self, model_id: str, reason: Optional[str] = None):
        """Registra falha (erro 500/timeout/saldo). Incrementa contador e abre circuito se necessário."""
        state = self._get_state(model_id)
        state['failures'] += 1
        state['last_failure'] = datetime.now()
        state['reason'] = reason or "unknown_error"
        
        if state['state'] == CircuitBreakerState.HALF_OPEN:
            # Falhou no teste de recuperação
            state['state'] = CircuitBreakerState.OPEN
            logger.warning(f"CircuitBreaker para {model_id} falhou no HALF-OPEN. Reabrindo. Motivo: {reason}")
            
        elif state['failures'] >= self.failure_threshold or reason in ["insufficient_balance", "quota_exceeded"]:
            # Para erros de saldo ou cota, abre o circuito IMEDIATAMENTE (threshold = 1)
            state['state'] = CircuitBreakerState.OPEN
            logger.warning(f"CircuitBreaker para {model_id} ABERTO. Motivo: {reason}")

    def _get_state(self, model_id: str) -> Dict:
        if model_id not in self._registry:
            self._registry[model_id] = {
                'failures': 0, 
                'last_failure': None, 
                'state': CircuitBreakerState.CLOSED,
                'reason': None
            }
        return self._registry[model_id]

# Singleton Global
circuit_breaker = ModelCircuitBreaker()

class AvailabilityService:
    def filter_available(self, candidates: list) -> list:
        """Retorna apenas modelos que não estão com Circuit Breaker aberto."""
        available = []
        for model in candidates:
            # Usa o nome canônico ou ID como chave
            key = str(model.id)
            if circuit_breaker.is_available(key):
                available.append(model)
        return available
