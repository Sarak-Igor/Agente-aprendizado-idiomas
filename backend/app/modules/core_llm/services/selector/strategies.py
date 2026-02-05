
from typing import List
from app.modules.core_llm.models.models import ModelCatalog
from .domain import SelectionStrategy, ModelCandidate

class RankingStrategies:
    """Implementa estratégias de ordenação de modelos."""
    
    def apply_strategy(self, candidates: List[ModelCatalog], strategy: SelectionStrategy) -> List[ModelCatalog]:
        if not candidates:
            return []
            
        if strategy == SelectionStrategy.PERFORMANCE:
            return self._rank_by_performance(candidates)
        elif strategy == SelectionStrategy.COST_BENEFIT:
            return self._rank_by_cost_benefit(candidates)
        elif strategy == SelectionStrategy.SPEED:
            return self._rank_by_speed(candidates)
        elif strategy == SelectionStrategy.CHEAPEST:
            return self._rank_by_cheapest(candidates)
        elif strategy == SelectionStrategy.FREE:
            return self._rank_by_free(candidates)
        else:
            return self._rank_by_performance(candidates) # Default

    def _rank_by_performance(self, models: List[ModelCatalog]) -> List[ModelCatalog]:
        """Elo Rating Descending."""
        # Se Elo for None, assume 0
        return sorted(models, key=lambda m: (m.elo_rating or 0), reverse=True)

    def _rank_by_cost_benefit(self, models: List[ModelCatalog]) -> List[ModelCatalog]:
        """
        Elo / (Average Price). 
        Como não temos preço no Catalog (está no Mapping), vamos usar heurística de nome para Custo 
        ou Performance bruta se não tivermos info de preço fácil.
        TODO: Fazer join com ProviderMapping para ter preço exato.
        Por enquanto: Prioriza Elo alto mas penaliza modelos 'ultra' ou 'opus' se tiver opção 'pro' boa.
        """
        def score(m):
            base = m.elo_rating or 1000
            name = m.display_name.lower()
            # Penalidade de custo estimada
            cost_factor = 1.0
            if "ultra" in name or "opus" in name or "gpt-4" in name:
                cost_factor = 3.0
            elif "pro" in name or "sonnet" in name:
                cost_factor = 1.5
            elif "flash" in name or "haiku" in name or "mini" in name:
                cost_factor = 0.5
            
            return base / cost_factor

        return sorted(models, key=score, reverse=True)

    def _rank_by_speed(self, models: List[ModelCatalog]) -> List[ModelCatalog]:
        """Prioriza modelos rápidos (Flash, Haiku, Mini)."""
        def speed_score(m):
            name = m.display_name.lower()
            if "flash" in name or "groq" in (m.source or ""):
                return 100
            if "haiku" in name or "mini" in name:
                return 80
            if "pro" in name or "turbo" in name:
                return 50
            return 10 # Ultra/Opus são lentos

        return sorted(models, key=speed_score, reverse=True)
        
    def _rank_by_cheapest(self, models: List[ModelCatalog]) -> List[ModelCatalog]:
         # TODO: Integrar com tabela de preços real
         return self._rank_by_speed(models) # Geralmente os rápidos são os mais baratos

    def _rank_by_free(self, models: List[ModelCatalog]) -> List[ModelCatalog]:
        """
        Retorna APENAS modelos gratuitos e os ordena por capacidade.
        """
        free_candidates = []
        
        for m in models:
            name = m.display_name.lower()
            score = 0
            
            # Heurística rigorosa para Grátis
            # Gemini Flash e Pro (via AI Studio/Gemini API) possuem Free Tier generoso
            if "gemini" in name and "flash" in name:
                score = 100
            elif "gemini" in name and "pro" in name:
                score = 80
            # Modelos Open Source via Groq (atualmente free trial/uso)
            elif "llama" in name or "gemma" in name or "mixtral" in name:
                # Se for OpenRouter, precisamos ser mais cuidadosos, pois lá quase tudo é pago.
                # Se a fonte for Groq, assumimos free/cheap por enquanto.
                if m.source == "groq":
                    score = 60
                else:
                    # No OpenRouter, filtramos pelo nome ou price (se tivéssemos price aqui)
                    # Por enquanto, se não for Gemini ou Groq, removemos se parecer 'premium'
                    if any(premium in name for premium in ["ultra", "opus", "large", "max"]):
                        continue
                    score = 10
            elif "mini" in name or "haiku" in name:
                score = 50
            else:
                # Se não temos certeza que é grátis, e a estratégia é FREE, melhor remover.
                continue
                
            if score > 0:
                # Atribui o score temporariamente para ordenação
                m._temp_score = score
                free_candidates.append(m)
            
        return sorted(free_candidates, key=lambda x: x._temp_score, reverse=True)
