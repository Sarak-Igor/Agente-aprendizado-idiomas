import random
import logging
from typing import List, Optional

from app.modules.agents.core_llm.services.orchestrator.base import LLMService
from app.modules.agents.core_llm.services.orchestrator.gemini_adapter import GeminiLLMService
from app.modules.agents.core_llm.services.orchestrator.providers import (
    OpenRouterLLMService,
    GroqLLMService,
    TogetherAILLMService,
)

logger = logging.getLogger(__name__)


def generate_phrase_with_llm(
    llm_service: LLMService,
    words: List[str],
    source_lang: str,
    target_lang: str,
    difficulty: str,
    custom_prompt: Optional[str] = None,
) -> dict:
    num_words = (
        random.randint(3, 7)
        if difficulty == "medium"
        else (random.randint(2, 4) if difficulty == "easy" else random.randint(5, 10))
    )
    selected_words = random.sample(words, min(num_words, len(words)))

    source_lang_name = "inglês" if source_lang == "en" else "português"
    target_lang_name = "português" if target_lang == "pt" else "inglês"

    difficulty_desc = {
        "easy": "frases curtas e simples, com vocabulário básico",
        "medium": "frases de tamanho médio, com vocabulário intermediário",
        "hard": "frases mais complexas, com vocabulário avançado",
    }

    if custom_prompt:
        prompt = custom_prompt.replace("{words}", ", ".join(selected_words))
        prompt = prompt.replace("{source_lang}", source_lang_name)
        prompt = prompt.replace("{target_lang}", target_lang_name)
        prompt = prompt.replace("{difficulty}", difficulty)
        prompt = prompt.replace("{difficulty_desc}", difficulty_desc.get(difficulty, ""))
    else:
        prompt = f"""Você é um professor de idiomas. Crie uma frase natural e completa em {source_lang_name} usando TODAS as seguintes palavras: {', '.join(selected_words)}

INSTRUÇÕES IMPORTANTES:
1. A frase deve ser natural, completa e fazer sentido gramaticalmente
2. Use TODAS as palavras fornecidas na frase
3. A frase deve ser adequada para nível {difficulty} de dificuldade ({difficulty_desc.get(difficulty, '')})
4. A frase deve ser uma sentença completa e coerente
5. NÃO adicione explicações, comentários ou prefixos como "Frase:" ou "A frase é:"
6. Retorne APENAS a frase criada, sem aspas, sem citações, sem nada além da frase

Exemplo de formato correto:
Se as palavras forem: ["love", "heart", "beautiful"]
Você deve retornar apenas: "I love your beautiful heart"

Agora crie a frase usando as palavras: {', '.join(selected_words)}"""

    try:
        original_phrase = llm_service.generate_text(prompt, max_tokens=200)
        original_phrase = original_phrase.strip()

        for prefix in [
            "Frase:",
            "Frase em",
            "Resposta:",
            "A frase:",
            "A frase é:",
            "Frase criada:",
            "Here is the phrase:",
            "The phrase is:",
        ]:
            if original_phrase.lower().startswith(prefix.lower()):
                original_phrase = original_phrase[len(prefix) :].strip()

        original_phrase = original_phrase.strip('"').strip("'").strip()
        if not original_phrase:
            raise Exception("Frase gerada está vazia")

        translation_prompt = f"""Traduza o seguinte texto de {source_lang_name} para {target_lang_name}.
Mantenha o mesmo tom e estilo. Retorne APENAS a tradução, sem explicações ou comentários.

Texto: {original_phrase}

Tradução:"""

        translated_phrase = llm_service.generate_text(translation_prompt, max_tokens=200)
        translated_phrase = translated_phrase.strip().strip('"').strip("'").strip()
        if not translated_phrase:
            raise Exception("Tradução gerada está vazia")

        model_name = None
        if isinstance(llm_service, GeminiLLMService):
            if hasattr(llm_service.gemini_service, "model"):
                model_name = llm_service.gemini_service.model
        elif isinstance(llm_service, OpenRouterLLMService):
            model_name = "openai/gpt-3.5-turbo"
        elif isinstance(llm_service, GroqLLMService):
            model_name = "llama-3.1-8b-instant"
        elif isinstance(llm_service, TogetherAILLMService):
            model_name = "meta-llama/Llama-3-8b-chat-hf"

        return {
            "phrase": {"original": original_phrase, "translated": translated_phrase},
            "model": model_name,
        }
    except Exception as e:
        logger.error(f"Erro ao gerar frase com LLM: {e}")
        raise


def generate_phrase_with_words(
    gemini_service,
    words: List[str],
    source_lang: str,
    target_lang: str,
    difficulty: str,
) -> dict:
    from app.modules.agents.core_llm.services.orchestrator.gemini_adapter import GeminiLLMService

    llm_service = GeminiLLMService(gemini_service)
    return generate_phrase_with_llm(llm_service, words, source_lang, target_lang, difficulty)

