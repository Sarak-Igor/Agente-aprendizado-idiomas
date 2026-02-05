"""
Serviço para rastrear uso de tokens por modelo e serviço
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.modules.core_llm.models.models import TokenUsage

logger = logging.getLogger(__name__)

class TokenUsageService:
    """Serviço para gerenciar rastreamento de uso de tokens de forma agnóstica"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_usage(
        self,
        service: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: Optional[int] = None,
        requests: int = 1,
        user_id = None
    ):
        """Registra uso de tokens para um modelo específico"""
        try:
            if user_id is None:
                logger.debug(f"Uso de tokens não registrado (user_id ausente): {service}/{model}")
                return
            
            if total_tokens is None:
                total_tokens = input_tokens + output_tokens
            
            usage = TokenUsage(
                user_id=user_id,
                service=service,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                requests=requests
            )
            
            self.db.add(usage)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Erro ao registrar uso de tokens: {e}")
            self.db.rollback()

    def get_usage_stats(self, user_id, days: int = 30) -> Dict:
        """Obtém estatísticas de uso agregadas e agrupadas por serviço"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 1. Estatísticas Totais
            total_result = self.db.query(
                func.sum(TokenUsage.input_tokens).label('total_input'),
                func.sum(TokenUsage.output_tokens).label('total_output'),
                func.sum(TokenUsage.total_tokens).label('total_tokens'),
                func.sum(TokenUsage.requests).label('total_requests')
            ).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= cutoff_date
            ).first()
            
            # 2. Estatísticas por Serviço
            service_results = self.db.query(
                TokenUsage.service,
                func.sum(TokenUsage.input_tokens).label('input_tokens'),
                func.sum(TokenUsage.output_tokens).label('output_tokens'),
                func.sum(TokenUsage.total_tokens).label('total_tokens'),
                func.sum(TokenUsage.requests).label('requests')
            ).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= cutoff_date
            ).group_by(TokenUsage.service).all()
            
            services_stats = []
            for s in service_results:
                # 3. Modelos para cada serviço
                model_results = self.db.query(
                    TokenUsage.model,
                    func.sum(TokenUsage.input_tokens).label('input_tokens'),
                    func.sum(TokenUsage.output_tokens).label('output_tokens'),
                    func.sum(TokenUsage.total_tokens).label('total_tokens'),
                    func.sum(TokenUsage.requests).label('requests')
                ).filter(
                    TokenUsage.user_id == user_id,
                    TokenUsage.service == s.service,
                    TokenUsage.created_at >= cutoff_date
                ).group_by(TokenUsage.model).all()
                
                services_stats.append({
                    'service': s.service,
                    'input_tokens': s.input_tokens or 0,
                    'output_tokens': s.output_tokens or 0,
                    'total_tokens': s.total_tokens or 0,
                    'requests': s.requests or 0,
                    'models': [
                        {
                            'model': m.model,
                            'input_tokens': m.input_tokens or 0,
                            'output_tokens': m.output_tokens or 0,
                            'tokens': m.total_tokens or 0,
                            'requests': m.requests or 0
                        } for m in model_results
                    ]
                })
            
            return {
                'total_input_tokens': total_result.total_input or 0,
                'total_output_tokens': total_result.total_output or 0,
                'total_tokens': total_result.total_tokens or 0,
                'total_requests': total_result.total_requests or 0,
                'services': services_stats,
                'period_days': days
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'total_input_tokens': 0, 'total_output_tokens': 0, 'total_tokens': 0, 'total_requests': 0,
                'services': [], 'period_days': days
            }
