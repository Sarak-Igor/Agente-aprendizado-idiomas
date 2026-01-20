"""
Script para verificar se o contexto está sendo salvo corretamente
Verifica:
1. Se mensagens estão sendo salvas no banco
2. Se campos de análise (topics, analysis_metadata) estão sendo preenchidos
3. Se o contexto da conversa está sendo construído corretamente
4. Se a análise assíncrona está funcionando
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.database import ChatSession, ChatMessage
from datetime import datetime, timedelta
import json

def verify_context_saving():
    """Verifica se o contexto está sendo salvo corretamente"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 60)
        print("VERIFICAÇÃO DE CONTEXTO E ANÁLISE")
        print("=" * 60)
        
        # 1. Verifica sessões recentes
        print("\n1. VERIFICANDO SESSÕES RECENTES...")
        recent_sessions = db.query(ChatSession).filter(
            ChatSession.is_active == True
        ).order_by(ChatSession.created_at.desc()).limit(5).all()
        
        if not recent_sessions:
            print("   [AVISO] Nenhuma sessao ativa encontrada")
            return
        
        print(f"   [OK] Encontradas {len(recent_sessions)} sessoes ativas")
        
        # 2. Verifica mensagens de cada sessão
        for session in recent_sessions:
            print(f"\n2. VERIFICANDO SESSÃO: {session.id}")
            print(f"   - Idioma: {session.language}")
            print(f"   - Modo: {session.mode}")
            print(f"   - Modelo: {session.model_service}/{session.model_name}")
            print(f"   - Criada em: {session.created_at}")
            
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.created_at).all()
            
            print(f"   - Total de mensagens: {len(messages)}")
            
            if not messages:
                print("   [AVISO] Nenhuma mensagem encontrada nesta sessao")
                continue
            
            # 3. Verifica cada mensagem
            user_messages_with_analysis = 0
            user_messages_without_analysis = 0
            
            for i, msg in enumerate(messages, 1):
                print(f"\n   Mensagem {i} ({msg.role}):")
                print(f"      - ID: {msg.id}")
                print(f"      - Conteúdo: {msg.content[:50]}..." if len(msg.content) > 50 else f"      - Conteúdo: {msg.content}")
                print(f"      - Criada em: {msg.created_at}")
                
                if msg.role == "user":
                    # Verifica campos de análise
                    has_grammar_errors = msg.grammar_errors is not None
                    has_vocabulary = msg.vocabulary_suggestions is not None
                    has_difficulty = msg.difficulty_score is not None
                    has_topics = msg.topics is not None
                    has_metadata = msg.analysis_metadata is not None
                    
                    print(f"      - Analise:")
                    print(f"         * Erros gramaticais: {'[OK]' if has_grammar_errors else '[FALTANDO]'}")
                    print(f"         * Sugestoes de vocabulario: {'[OK]' if has_vocabulary else '[FALTANDO]'}")
                    print(f"         * Score de dificuldade: {'[OK]' if has_difficulty else '[FALTANDO]'}")
                    print(f"         * Topicos: {'[OK]' if has_topics else '[FALTANDO]'}")
                    print(f"         * Metadados: {'[OK]' if has_metadata else '[FALTANDO]'}")
                    
                    if has_grammar_errors or has_vocabulary or has_topics or has_metadata:
                        user_messages_with_analysis += 1
                        
                        # Mostra detalhes se disponível
                        if has_grammar_errors:
                            errors = msg.grammar_errors if isinstance(msg.grammar_errors, list) else json.loads(msg.grammar_errors) if isinstance(msg.grammar_errors, str) else {}
                            print(f"         • Número de erros: {len(errors) if isinstance(errors, list) else 'N/A'}")
                        
                        if has_topics:
                            topics = msg.topics if isinstance(msg.topics, list) else json.loads(msg.topics) if isinstance(msg.topics, str) else {}
                            print(f"         • Número de tópicos: {len(topics) if isinstance(topics, list) else 'N/A'}")
                        
                        if has_metadata:
                            metadata = msg.analysis_metadata if isinstance(msg.analysis_metadata, dict) else json.loads(msg.analysis_metadata) if isinstance(msg.analysis_metadata, str) else {}
                            if isinstance(metadata, dict):
                                print(f"         • Versão do analisador: {metadata.get('analyzer_version', 'N/A')}")
                                print(f"         • Tempo de processamento: {metadata.get('processing_time_ms', 'N/A')}ms")
                                print(f"         • Idioma original: {metadata.get('original_language', 'N/A')}")
                    else:
                        user_messages_without_analysis += 1
                        # Verifica se a mensagem é recente (menos de 2 minutos)
                        age = datetime.utcnow() - msg.created_at.replace(tzinfo=None)
                        if age < timedelta(minutes=2):
                            print(f"         [AGUARDANDO] Analise ainda em processamento (mensagem recente)")
                        else:
                            print(f"         [AVISO] Analise nao foi executada ou falhou")
                
                elif msg.role == "assistant":
                    if msg.feedback_type:
                        print(f"      - Tipo de feedback: {msg.feedback_type}")
            
            # 4. Verifica contexto da conversa
            print(f"\n   CONTEXTO DA CONVERSA:")
            if len(messages) > 0:
                # Simula construção de contexto
                context_parts = []
                recent_messages = messages[-10:] if len(messages) > 10 else messages
                
                for msg in recent_messages:
                    if msg.role == "user":
                        content = msg.transcription if msg.transcription else msg.content
                        context_parts.append(f"Aluno: {content[:50]}...")
                    elif msg.role == "assistant":
                        context_parts.append(f"Professor: {msg.content[:50]}...")
                
                print(f"      - Últimas {len(recent_messages)} mensagens no contexto")
                print(f"      - Tamanho do contexto: {len('\\n'.join(context_parts))} caracteres")
                print(f"      - Preview do contexto:")
                for part in context_parts[-3:]:  # Mostra últimas 3
                    print(f"         {part}")
            else:
                print(f"      [AVISO] Nenhuma mensagem para construir contexto")
            
            # 5. Estatísticas
            print(f"\n   ESTATISTICAS:")
            print(f"      - Mensagens do usuario: {sum(1 for m in messages if m.role == 'user')}")
            print(f"      - Mensagens do assistente: {sum(1 for m in messages if m.role == 'assistant')}")
            print(f"      - Mensagens com analise completa: {user_messages_with_analysis}")
            print(f"      - Mensagens sem analise: {user_messages_without_analysis}")
            
            if user_messages_with_analysis > 0:
                print(f"      [OK] Analise esta funcionando!")
            else:
                print(f"      [AVISO] Nenhuma mensagem com analise completa encontrada")
        
        print("\n" + "=" * 60)
        print("VERIFICAÇÃO CONCLUÍDA")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante verificacao: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_context_saving()
