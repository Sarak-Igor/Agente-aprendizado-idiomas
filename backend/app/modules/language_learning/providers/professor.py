"""
Provedor de prompts para o professor de idiomas
"""
from typing import Optional, Dict
from app.modules.user_intelligence.models.models import ChatSession, UserProfile

class ProfessorPromptProvider:
    """Fornece prompts específicos para o ensino de idiomas"""
    
    @staticmethod
    def get_system_prompt(session: ChatSession, user_profile: Optional[UserProfile]) -> str:
        """Constrói o prompt do sistema para o professor"""
        if session.custom_prompt and session.custom_prompt.strip():
            return session.custom_prompt.strip()
            
        language_names = {
            'pt': 'português', 'en': 'inglês', 'es': 'espanhol', 'fr': 'francês',
            'de': 'alemão', 'it': 'italiano', 'ja': 'japonês', 'ko': 'coreano',
            'zh': 'chinês', 'ru': 'russo'
        }
        
        teaching_lang = session.teaching_language if session.teaching_language else session.language
        learning_language = language_names.get(teaching_lang, teaching_lang)
        native_language = "português"
        proficiency = "iniciante"
        
        if user_profile:
            native_language = language_names.get(user_profile.native_language, user_profile.native_language)
            proficiency = {
                'beginner': 'iniciante',
                'intermediate': 'intermediário',
                'advanced': 'avançado'
            }.get(user_profile.proficiency_level, 'iniciante')
            
        if session.mode == "writing":
            return f"""Você é um professor de {learning_language} experiente e paciente. Seu aluno é {proficiency} e fala {native_language} como idioma nativo.

MODO: ESCRITA
- Avalie a escrita do aluno
- Corrija erros gramaticais de forma clara e didática
- Explique as correções quando necessário
- Forneça sugestões de vocabulário mais apropriado
- Seja encorajador e positivo
- Use {native_language} para explicações quando necessário
- Mantenha o foco em melhorar a escrita do aluno

Comece a conversa de forma amigável e pergunte sobre o que o aluno gostaria de praticar hoje."""
        else:
            return f"""Você é um professor de {learning_language} experiente e paciente. Seu aluno é {proficiency} e fala {native_language} como idioma nativo.

MODO: CONVERSA
- Converse naturalmente em {learning_language}
- Ajuste a complexidade do vocabulário ao nível do aluno ({proficiency})
- Faça perguntas interessantes para manter a conversa fluindo
- Corrija erros de forma sutil e natural
- Use {native_language} apenas quando necessário para explicações
- Seja encorajador e crie um ambiente descontraído

Comece a conversa de forma natural e amigável."""

    @staticmethod
    def analyze_feedback_type(response: str) -> Optional[str]:
        """Analisa o tipo de feedback contido na resposta"""
        response_lower = response.lower()
        if any(word in response_lower for word in ['correto', 'correção', 'erro', 'deveria ser']):
            return "correction"
        elif any(word in response_lower for word in ['explicação', 'porque', 'razão', 'motivo']):
            return "explanation"
        elif any(word in response_lower for word in ['parabéns', 'bom trabalho', 'excelente', 'ótimo']):
            return "encouragement"
        return None
