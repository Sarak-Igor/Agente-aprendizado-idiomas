"""
Script para verificar se o contexto das mensagens está sendo salvo corretamente
"""
from app.database import SessionLocal
from app.models.database import ChatSession, ChatMessage
from sqlalchemy import desc
import json

def verify_messages_context():
    """Verifica se as mensagens e contexto estão sendo salvos corretamente"""
    db = SessionLocal()
    
    try:
        # Busca a sessão mais recente
        latest_session = db.query(ChatSession).order_by(desc(ChatSession.created_at)).first()
        
        if not latest_session:
            print("Nenhuma sessão encontrada no banco de dados.")
            return
        
        print(f"\n{'='*80}")
        print(f"SESSÃO ENCONTRADA:")
        print(f"{'='*80}")
        print(f"ID: {latest_session.id}")
        print(f"Modo: {latest_session.mode}")
        print(f"Idioma: {latest_session.language}")
        print(f"Idioma de ensino: {latest_session.teaching_language}")
        print(f"Modelo: {latest_session.model_service}/{latest_session.model_name}")
        print(f"Mensagens na sessão: {latest_session.message_count}")
        print(f"Ativa: {latest_session.is_active}")
        print(f"Criada em: {latest_session.created_at}")
        print(f"Atualizada em: {latest_session.updated_at}")
        
        # Busca todas as mensagens da sessão
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == latest_session.id
        ).order_by(ChatMessage.created_at).all()
        
        print(f"\n{'='*80}")
        print(f"MENSAGENS ENCONTRADAS: {len(messages)}")
        print(f"{'='*80}")
        
        if len(messages) == 0:
            print("Nenhuma mensagem encontrada nesta sessão.")
            return
        
        for i, msg in enumerate(messages, 1):
            print(f"\n--- Mensagem {i} ---")
            print(f"ID: {msg.id}")
            print(f"Role: {msg.role}")
            print(f"Tipo de conteúdo: {msg.content_type}")
            print(f"Conteúdo: {msg.content[:200]}..." if len(msg.content) > 200 else f"Conteúdo: {msg.content}")
            print(f"Criada em: {msg.created_at}")
            
            # Verifica campos de análise
            if msg.grammar_errors:
                print(f"Erros gramaticais: {len(msg.grammar_errors)} encontrados")
            if msg.vocabulary_suggestions:
                print(f"Sugestões de vocabulário: {len(msg.vocabulary_suggestions)} encontradas")
            if msg.difficulty_score is not None:
                print(f"Pontuação de dificuldade: {msg.difficulty_score}")
            if msg.topics:
                print(f"Tópicos: {msg.topics}")
            if msg.analysis_metadata:
                print(f"Metadados de análise: {json.dumps(msg.analysis_metadata, indent=2, ensure_ascii=False)}")
        
        # Verifica se há contexto salvo na sessão
        print(f"\n{'='*80}")
        print(f"CONTEXTO DA SESSÃO:")
        print(f"{'='*80}")
        if latest_session.session_context:
            print(f"Contexto salvo: {json.dumps(latest_session.session_context, indent=2, ensure_ascii=False)}")
        else:
            print("Nenhum contexto salvo na sessão (isso é normal, o contexto é construído dinamicamente)")
        
        # Verifica se o prompt está sendo usado
        print(f"\n{'='*80}")
        print(f"CONFIGURAÇÕES DO PROFESSOR:")
        print(f"{'='*80}")
        print(f"Prompt personalizado: {'Sim' if latest_session.custom_prompt else 'Não (usando padrão)'}")
        if latest_session.custom_prompt:
            print(f"Prompt: {latest_session.custom_prompt[:200]}..." if len(latest_session.custom_prompt) > 200 else f"Prompt: {latest_session.custom_prompt}")
        
        # Verifica se há mensagem inicial do assistente (que contém o prompt)
        initial_assistant_msg = next((m for m in messages if m.role == "assistant" and len(m.content) > 200), None)
        if initial_assistant_msg:
            print(f"\nMensagem inicial do assistente encontrada (contém prompt do sistema)")
            print(f"Tamanho: {len(initial_assistant_msg.content)} caracteres")
        
        print(f"\n{'='*80}")
        print(f"VERIFICAÇÃO CONCLUÍDA")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Erro ao verificar contexto: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_messages_context()
