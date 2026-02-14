
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database import ModelCatalog, UserProfile
from .domain import SelectionRequest, SelectionResult, ModelCandidate, SelectionStrategy
from .capability_filter import CapabilityFilterService
from .availability_service import AvailabilityService
from .strategies import RankingStrategies
import logging

logger = logging.getLogger(__name__)

class UniversalModelSelector:
    def __init__(self, db: Session):
        self.db = db
        self.cap_filter = CapabilityFilterService()
        self.availability = AvailabilityService()
        self.ranker = RankingStrategies()

    def select_model(self, request: SelectionRequest) -> SelectionResult:
        """
        Orquestra a seleção do melhor modelo para a requisição.
        """
        # 1. Carregar Candidatos (Ativos)
        candidates = self.db.query(ModelCatalog).filter(ModelCatalog.is_active == True).all()
        
        if not candidates:
            raise ValueError("Nenhum modelo ativo encontrado no catálogo.")
            
        # 2. Resolver Estratégia
        strategy = request.strategy
        if not strategy:
            strategy = self._resolve_user_preference(request.user_id, request)
            
        decision_log = [f"Initial candidates: {len(candidates)}", f"Category: {request.agent_category}", f"Strategy: {strategy}"]
        notices = []
        
        # 3. Filtro de Capacidades
        candidates = self.cap_filter.filter_by_capabilities(candidates, request.required_capabilities)
        decision_log.append(f"After Capability Filter ({request.required_capabilities}): {len(candidates)}")
        
        if not candidates:
             # Fallback crítico: se não tem modelo com capacidade, tenta degradar ou erro.
             # Por enquanto erro.
             raise ValueError(f"Nenhum modelo encontrado com capacidades: {request.required_capabilities}")

        # 4. Filtro de Disponibilidade (Circuit Breaker)
        available_candidates = self.availability.filter_available(candidates)
        decision_log.append(f"After Availability Filter: {len(available_candidates)}")
        
        # Se todos os principais estiverem em Circuit Breaker, talvez devêssemos tentar forçar um (fail fast)
        # ou pegar o menos pior. Por enquanto, se lista vazia, pega o primeiro da lista de capabilities (ignore closed breaker for now to force retry?)
        # Não, better fail e deixar o usuario tentar de novo ou o sistema retentar.
        if not available_candidates:
            logger.warning("Todos os modelos candidatos estao indisponiveis (Circuit Breaker). Usando fallback de capabilities.")
            available_candidates = candidates # Force try se todos down
            decision_log.append("WARNING: All candidates down. Forcing retry on raw candidates.")
        
        # 4.1 Detecção de Fallbacks de Custo/Cota para Avisos ao Usuário
        # Se os melhores modelos filtrados por capability estão fora por Circuit Breaker
        # e o motivo foi saldo/cota, geramos um notice.
        top_candidates = candidates[:3] # Pega os 3 melhores originais
        for tc in top_candidates:
            state = self.availability.circuit_breaker._get_state(str(tc.id))
            if state['state'] == "open" and state['reason'] == "insufficient_balance":
                notice = "Sua estratégia de performance está limitada por saldo insuficiente nos provedores premium. Migrando para fallbacks disponíveis."
                if notice not in notices: notices.append(notice)
            elif state['state'] == "open" and state['reason'] == "quota_exceeded":
                notice = "Cota de requisições atingida nos modelos principais. Usando alternativas disponíveis."
                if notice not in notices: notices.append(notice)
        
        # Se a estratégia for FREE e houveram modelos filtrados que não eram free
        if strategy == SelectionStrategy.FREE:
            # A filtragem agora acontece dentro do ranker._rank_by_free (Phase 10)
            pass

        # 5. Ranking
        ranked = self.ranker.apply_strategy(available_candidates, strategy)
        
        # 6. Montar Resultado
        # Mapeia ModelCatalog -> ModelCandidate
        final_candidates = [self._to_candidate(m) for m in ranked]
        
        selected = final_candidates[0]
        alternatives = final_candidates[1:]
        
        logger.info(f"Model Selected: {selected.model} (Strategy: {strategy})")
        
        return SelectionResult(
            selected_model=selected,
            alternatives=alternatives,
            strategy_used=strategy,
            decision_log=decision_log,
            notices=notices
        )

    def _resolve_user_preference(self, user_id: str, request: SelectionRequest) -> SelectionStrategy:
        """Busca preferência no UserProfile, seguindo a hierarquia de prioridades."""
        from .domain import SelectionStrategy, AgentCategory
        try:
            profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile and profile.model_preferences:
                prefs = profile.model_preferences
                
                # 1. Master Toggle: Se o modo for estritamente gratuito, ignora o resto
                if prefs.get("usage_mode") == "free":
                    return SelectionStrategy.FREE
                
                # 2. Preferência por Categoria Especializada (ex: chat_strategy, code_strategy)
                category_key = f"{request.agent_category.value}_strategy"
                category_pref = prefs.get(category_key)
                
                # Se a preferência for "global" ou não existir, busca a global_strategy
                if category_pref and category_pref != "global":
                    try:
                        return SelectionStrategy(category_pref)
                    except ValueError:
                        pass # Valor inválido, tenta o próximo nível
                
                # 3. Estratégia Global Unificada
                global_pref = prefs.get("global_strategy")
                if global_pref:
                    try:
                        return SelectionStrategy(global_pref)
                    except ValueError:
                        pass
                
                # 4. Fallback Legado (Função específica)
                func_pref = prefs.get(request.function_name)
                if func_pref:
                    try:
                        return SelectionStrategy(func_pref)
                    except ValueError:
                        pass
                        
        except Exception as e:
            logger.warning(f"Erro ao resolver preferencia de usuario: {e}")
            
        return SelectionStrategy.PERFORMANCE # Default absoluto

    def _to_candidate(self, model: ModelCatalog) -> ModelCandidate:
        # Tenta achar o provider
        # Simplificação: assume que o primeiro mapping é o principal ou usa source
        provider = "google" # Default
        if model.source == "openrouter":
            provider = "openrouter"
        elif "gpt" in model.display_name.lower():
            provider = "openai" # ou via mapping
        
        # O nome do modelo para API muitas vezes não é o display_name
        # Idealmente teriamos join com ModelProviderMapping.
        # Por hora vamos assumir que o sistema sabe lidar com o canonical_name ou ID.
        # Vamos passar o ID do catalogo e o backend que se vire para achar o provider_model_id?
        # Não, o Seletor tem que entregar mastigado.
        
        # TODO: Refatorar para fazer join com ModelProviderMapping e retornar o ID real da API.
        # Para MVP, vamos assumir que aliases[0] ou display_name funciona.
        
        api_model_name = model.display_name # Temp
        
        return ModelCandidate(
            model=api_model_name,
            provider=provider,
            elo_score=model.elo_rating or 0,
            db_model={"id": str(model.id), "display_name": model.display_name}
        )
