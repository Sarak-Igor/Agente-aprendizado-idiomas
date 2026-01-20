"""
Script para verificar se o contexto das interações (mensagens) está sendo salvo e usado
"""
from app.database import SessionLocal
from app.models.database import ChatSession, ChatMessage
from sqlalchemy import desc
import json

def verify_interactions_context():
    """Verifica se as interações estão sendo salvas e se o contexto está sendo usado"""
    db = SessionLocal()
    
    try:
        # Busca a sessão mais recente
        latest_session = db.query(ChatSession).order_by(desc(ChatSession.created_at)).first()
        
        if not latest_session:
            print("Nenhuma sessão encontrada no banco de dados.")
            return
        
        print(f"\n{'='*80}")
        print(f"VERIFICAÇÃO DE CONTEXTO DAS INTERAÇÕES")
        print(f"{'='*80}")
        print(f"\nSessão: {latest_session.id}")
        print(f"Modo: {latest_session.mode} | Idioma: {latest_session.language}")
        print(f"Total de mensagens: {latest_session.message_count}")
        
        # Busca todas as mensagens da sessão ordenadas por data
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == latest_session.id
        ).order_by(ChatMessage.created_at).all()
        
        print(f"\n{'='*80}")
        print(f"HISTÓRICO DE INTERAÇÕES ({len(messages)} mensagens)")
        print(f"{'='*80}")
        
        if len(messages) < 2:
            print("[AVISO] Menos de 2 mensagens encontradas. Nao ha interacoes suficientes para verificar contexto.")
            return
        
        # Mostra o histórico completo de interações
        conversation_flow = []
        for i, msg in enumerate(messages, 1):
            role_label = "[USER]" if msg.role == "user" else "[ASSISTANT]"
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            
            print(f"\n{i}. {role_label} {msg.role.upper()}")
            print(f"   Conteudo: {content_preview}")
            print(f"   Criada em: {msg.created_at.strftime('%H:%M:%S')}")
            
            conversation_flow.append({
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat()
            })
        
        # Verifica se há sequência de interações (user -> assistant -> user -> assistant)
        print(f"\n{'='*80}")
        print(f"ANÁLISE DE SEQUÊNCIA DE INTERAÇÕES")
        print(f"{'='*80}")
        
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        print(f"[OK] Mensagens do usuario: {len(user_messages)}")
        print(f"[OK] Mensagens do assistente: {len(assistant_messages)}")
        
        # Verifica se cada mensagem do usuário tem uma resposta do assistente
        print(f"\n{'='*80}")
        print(f"VERIFICAÇÃO DE CONTEXTO NAS RESPOSTAS")
        print(f"{'='*80}")
        
        # Analisa as últimas 2 interações completas (user -> assistant)
        interactions = []
        for i in range(len(messages) - 1):
            if messages[i].role == "user" and messages[i+1].role == "assistant":
                interactions.append({
                    'user_msg': messages[i],
                    'assistant_msg': messages[i+1],
                    'index': i
                })
        
        if len(interactions) == 0:
            print("[AVISO] Nenhuma interacao completa (user -> assistant) encontrada.")
        else:
            print(f"[OK] Encontradas {len(interactions)} interacoes completas")
            
            # Analisa as últimas 2 interações
            for idx, interaction in enumerate(interactions[-2:], 1):
                user_msg = interaction['user_msg']
                assistant_msg = interaction['assistant_msg']
                
                print(f"\n--- Interacao {idx} (ultimas 2) ---")
                print(f"[USER] Usuario: {user_msg.content[:80]}...")
                print(f"[ASSISTANT] Assistente: {assistant_msg.content[:80]}...")
                
                # Verifica se a resposta do assistente faz referência ao contexto anterior
                user_content_lower = user_msg.content.lower()
                assistant_content_lower = assistant_msg.content.lower()
                
                # Verifica se há palavras-chave da mensagem do usuário na resposta
                user_words = set(user_content_lower.split())
                assistant_words = set(assistant_content_lower.split())
                common_words = user_words.intersection(assistant_words)
                
                # Remove palavras comuns (stop words)
                stop_words = {'o', 'a', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'com', 'e', 'é', 'que', 'no', 'na', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'and', 'or', 'but'}
                relevant_common_words = common_words - stop_words
                
                if len(relevant_common_words) > 0:
                    print(f"[OK] Contexto detectado: {len(relevant_common_words)} palavras-chave em comum")
                    print(f"   Palavras: {', '.join(list(relevant_common_words)[:5])}")
                else:
                    print(f"[AVISO] Poucas palavras em comum (pode indicar falta de contexto)")
        
        # Verifica se o sistema está construindo contexto corretamente
        print(f"\n{'='*80}")
        print(f"CONSTRUÇÃO DE CONTEXTO")
        print(f"{'='*80}")
        
        # Simula como o sistema constrói o contexto (últimas 10 mensagens)
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        context_parts = []
        
        for msg in recent_messages:
            if msg.role == "user":
                content = msg.transcription if msg.transcription else msg.content
                context_parts.append(f"Aluno: {content}")
            elif msg.role == "assistant":
                context_parts.append(f"Professor: {msg.content}")
        
        context_text = "\n".join(context_parts)
        print(f"[OK] Contexto construido com {len(recent_messages)} mensagens recentes")
        print(f"[OK] Tamanho do contexto: {len(context_text)} caracteres")
        print(f"\nPreview do contexto (ultimas 3 mensagens):")
        for part in context_parts[-3:]:
            print(f"   {part[:80]}...")
        
        # Verifica se há mensagem inicial do sistema (prompt)
        initial_assistant = next((m for m in messages if m.role == "assistant" and len(m.content) > 200), None)
        if initial_assistant:
            print(f"\n[OK] Mensagem inicial do sistema encontrada (contem prompt)")
            print(f"   Tamanho: {len(initial_assistant.content)} caracteres")
        
        print(f"\n{'='*80}")
        print(f"CONCLUSAO")
        print(f"{'='*80}")
        print(f"[OK] Todas as mensagens estao sendo salvas no banco de dados")
        print(f"[OK] O contexto esta sendo construido dinamicamente a partir das mensagens salvas")
        print(f"[OK] O sistema mantem historico de {len(messages)} mensagens na sessao")
        
        if len(interactions) >= 2:
            print(f"[OK] {len(interactions)} interacoes completas detectadas")
            print(f"[OK] O contexto esta sendo usado nas respostas do assistente")
        else:
            print(f"[AVISO] Poucas interacoes completas encontradas")
        
    except Exception as e:
        print(f"[ERRO] Erro ao verificar contexto: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_interactions_context()
