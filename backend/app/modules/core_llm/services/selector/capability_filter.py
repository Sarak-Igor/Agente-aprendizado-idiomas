
from typing import List, Set
from app.modules.core_llm.models.models import ModelCatalog, ModelProviderMapping
from .domain import ModelCapability

class CapabilityFilterService:
    """
    Filtra modelos candidatos baseado nas capacidades técnicas exigidas.
    """
    
    def filter_by_capabilities(self, 
                               candidates: List[ModelCatalog], 
                               required_caps: List[ModelCapability]) -> List[ModelCatalog]:
        """
        Retorna apenas os modelos que possuem TODAS as capacidades exigidas.
        """
        if not required_caps:
            return candidates
            
        filtered = []
        required_set = {cap.value for cap in required_caps}
        
        for model in candidates:
            # Garante que capabilities é uma lista de strings
            model_caps = set(model.capabilities) if model.capabilities else set()
            
            # Se 'text_input' for requerido, quase todos têm, mas vamos checar explicitamente
            # Alguns modelos de embedding ou audio-only podem não ter text-input (raro em LLM chat)
            
            if required_set.issubset(model_caps):
                filtered.append(model)
                
        return filtered

    def filter_by_provider_availability(self, 
                                      candidates: List[ModelCatalog], 
                                      active_providers: Set[str]) -> List[ModelCatalog]:
        """
        Filtra modelos cujos provedores (via Mapping) estão ativos/configurados pelo usuário.
        Esta etapa exige um join com ModelProviderMapping.
        """
        # TODO: Implementar lógica de verificação de API Key ativa no UserProfile/System
        # Por enquanto assume que se está no catálogo ativo, está valendo.
        return [m for m in candidates if m.is_active]
