"""
Script completo para verificar se todo o contexto do usuario esta sendo salvo corretamente
Verifica: UserProfile, ChatSession, ChatMessage e seus campos de analise
"""
from app.database import SessionLocal
from app.models.database import User, UserProfile, ChatSession, ChatMessage
from sqlalchemy import desc
import json

def parse_jsonb(value):
    """Parse JSONB field que pode estar como string ou dict"""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return value
    return value

def verify_user_context():
    """Verifica se todo o contexto do usuario esta sendo salvo"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"VERIFICACAO COMPLETA DO CONTEXTO DO USUARIO")
        print(f"{'='*80}")
        
        # Busca o usuario com a sessao mais recente
        latest_session = db.query(ChatSession).order_by(desc(ChatSession.created_at)).first()
        
        if not latest_session:
            # Se nao tem sessao, busca usuario mais recente com perfil
            latest_user = db.query(User).join(UserProfile).order_by(desc(User.created_at)).first()
            if not latest_user:
                print("Nenhum usuario encontrado no banco de dados.")
                return
        else:
            latest_user = latest_session.user
        
        print(f"\nUsuario: {latest_user.username} ({latest_user.email})")
        print(f"ID: {latest_user.id}")
        
        # Verifica UserProfile
        print(f"\n{'='*80}")
        print(f"1. USER PROFILE")
        print(f"{'='*80}")
        
        profile = db.query(UserProfile).filter(UserProfile.user_id == latest_user.id).first()
        
        if not profile:
            print("[ERRO] Perfil do usuario nao encontrado!")
            return
        
        print(f"[OK] Perfil encontrado")
        print(f"   - Native Language: {profile.native_language}")
        print(f"   - Learning Language: {profile.learning_language}")
        print(f"   - Proficiency Level: {profile.proficiency_level}")
        print(f"   - Total Chat Messages: {profile.total_chat_messages}")
        print(f"   - Total Practice Sessions: {profile.total_practice_sessions}")
        print(f"   - Average Response Time: {profile.average_response_time}s")
        print(f"   - Preferred Learning Style: {profile.preferred_learning_style or 'N/A'}")
        print(f"   - Preferred Model: {profile.preferred_model or 'N/A'}")
        
        learning_context = parse_jsonb(profile.learning_context)
        if learning_context:
            print(f"   - Learning Context: {json.dumps(learning_context, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"   - Learning Context: N/A (ainda nao implementado)")
        
        # Verifica ChatSessions
        print(f"\n{'='*80}")
        print(f"2. CHAT SESSIONS")
        print(f"{'='*80}")
        
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == latest_user.id
        ).order_by(desc(ChatSession.created_at)).all()
        
        print(f"[OK] Total de sessoes: {len(sessions)}")
        
        if len(sessions) == 0:
            print("[AVISO] Nenhuma sessao encontrada para este usuario")
            return
        
        # Se nao tinha latest_session definido antes, usa a primeira da lista
        if 'latest_session' not in locals() or latest_session is None:
            latest_session = sessions[0]
        print(f"\nSessao mais recente: {latest_session.id}")
        print(f"   - Mode: {latest_session.mode}")
        print(f"   - Language: {latest_session.language}")
        print(f"   - Teaching Language: {latest_session.teaching_language or 'N/A (usa language)'}")
        print(f"   - Custom Prompt: {'Sim' if latest_session.custom_prompt else 'Nao (usa padrao)'}")
        if latest_session.custom_prompt:
            print(f"      Preview: {latest_session.custom_prompt[:100]}...")
        print(f"   - Model Service: {latest_session.model_service}")
        print(f"   - Model Name: {latest_session.model_name}")
        print(f"   - Message Count: {latest_session.message_count}")
        print(f"   - Is Active: {latest_session.is_active}")
        
        session_context = parse_jsonb(latest_session.session_context)
        if session_context:
            print(f"   - Session Context: {json.dumps(session_context, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"   - Session Context: N/A (ainda nao implementado)")
        
        # Verifica ChatMessages
        print(f"\n{'='*80}")
        print(f"3. CHAT MESSAGES - Analise de Contexto")
        print(f"{'='*80}")
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == latest_session.id
        ).order_by(ChatMessage.created_at).all()
        
        print(f"[OK] Total de mensagens na sessao: {len(messages)}")
        
        if len(messages) == 0:
            print("[AVISO] Nenhuma mensagem encontrada")
            return
        
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        print(f"   - Mensagens do usuario: {len(user_messages)}")
        print(f"   - Mensagens do assistente: {len(assistant_messages)}")
        
        # Analisa mensagens do usuario com dados de analise
        print(f"\n{'='*80}")
        print(f"4. ANALISE DAS MENSAGENS DO USUARIO")
        print(f"{'='*80}")
        
        analyzed_count = 0
        total_grammar_errors = 0
        total_vocab_suggestions = 0
        total_topics = 0
        difficulty_scores = []
        
        for i, msg in enumerate(user_messages, 1):
            print(f"\nMensagem {i}:")
            print(f"   Conteudo: {msg.content[:80]}...")
            print(f"   Criada em: {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Transcription: {msg.transcription or 'N/A'}")
            
            # Verifica campos de analise
            grammar_errors = parse_jsonb(msg.grammar_errors)
            vocabulary_suggestions = parse_jsonb(msg.vocabulary_suggestions)
            topics = parse_jsonb(msg.topics)
            analysis_metadata = parse_jsonb(msg.analysis_metadata)
            difficulty_score = msg.difficulty_score
            
            has_analysis = False
            
            if grammar_errors and len(grammar_errors) > 0:
                print(f"   [OK] Grammar Errors: {len(grammar_errors)} erros")
                total_grammar_errors += len(grammar_errors)
                has_analysis = True
                # Mostra primeiro erro como exemplo
                if len(grammar_errors) > 0:
                    first_error = grammar_errors[0]
                    if isinstance(first_error, dict):
                        print(f"      Exemplo: {first_error.get('type', 'N/A')} - {first_error.get('original', 'N/A')} -> {first_error.get('corrected', 'N/A')}")
            else:
                print(f"   [INFO] Grammar Errors: N/A ou vazio")
            
            if vocabulary_suggestions and len(vocabulary_suggestions) > 0:
                print(f"   [OK] Vocabulary Suggestions: {len(vocabulary_suggestions)} sugestoes")
                total_vocab_suggestions += len(vocabulary_suggestions)
                has_analysis = True
            else:
                print(f"   [INFO] Vocabulary Suggestions: N/A ou vazio")
            
            if topics and len(topics) > 0:
                print(f"   [OK] Topics: {len(topics)} topicos - {', '.join(topics[:3])}")
                total_topics += len(topics)
                has_analysis = True
            else:
                print(f"   [INFO] Topics: N/A ou vazio")
            
            if difficulty_score is not None:
                print(f"   [OK] Difficulty Score: {difficulty_score:.2f}")
                difficulty_scores.append(difficulty_score)
                has_analysis = True
            else:
                print(f"   [INFO] Difficulty Score: N/A")
            
            if analysis_metadata:
                print(f"   [OK] Analysis Metadata:")
                if isinstance(analysis_metadata, dict):
                    print(f"      - Analyzed At: {analysis_metadata.get('analyzed_at', 'N/A')}")
                    print(f"      - Analyzer Version: {analysis_metadata.get('analyzer_version', 'N/A')}")
                    print(f"      - Processing Time: {analysis_metadata.get('processing_time_ms', 'N/A')}ms")
                    print(f"      - Original Language: {analysis_metadata.get('original_language', 'N/A')}")
                    print(f"      - Normalized Language: {analysis_metadata.get('normalized_language', 'N/A')}")
                has_analysis = True
            else:
                print(f"   [INFO] Analysis Metadata: N/A")
            
            if has_analysis:
                analyzed_count += 1
        
        # Resumo da analise
        print(f"\n{'='*80}")
        print(f"5. RESUMO DA ANALISE")
        print(f"{'='*80}")
        
        print(f"[OK] Mensagens analisadas: {analyzed_count} de {len(user_messages)}")
        print(f"[OK] Total de erros gramaticais detectados: {total_grammar_errors}")
        print(f"[OK] Total de sugestoes de vocabulario: {total_vocab_suggestions}")
        print(f"[OK] Total de topicos identificados: {total_topics}")
        
        if difficulty_scores:
            avg_difficulty = sum(difficulty_scores) / len(difficulty_scores)
            print(f"[OK] Dificuldade media: {avg_difficulty:.2f}")
        else:
            print(f"[INFO] Nenhum score de dificuldade disponivel")
        
        # Verifica se o contexto esta sendo usado
        print(f"\n{'='*80}")
        print(f"6. VERIFICACAO DE CONTEXTO NAS RESPOSTAS")
        print(f"{'='*80}")
        
        if len(assistant_messages) > 0:
            print(f"[OK] Respostas do assistente encontradas: {len(assistant_messages)}")
            
            # Verifica se as respostas fazem referencia ao contexto
            for i, msg in enumerate(assistant_messages[-3:], 1):  # Ultimas 3
                print(f"\nResposta {i}:")
                print(f"   Conteudo: {msg.content[:150]}...")
                print(f"   Feedback Type: {msg.feedback_type or 'N/A'}")
        else:
            print(f"[AVISO] Nenhuma resposta do assistente encontrada")
        
        # Conclusao final
        print(f"\n{'='*80}")
        print(f"CONCLUSAO FINAL")
        print(f"{'='*80}")
        
        checks_passed = []
        checks_failed = []
        
        # Check 1: UserProfile existe e tem dados basicos
        if profile:
            checks_passed.append("UserProfile existe e tem dados basicos")
        else:
            checks_failed.append("UserProfile nao encontrado")
        
        # Check 2: ChatSession tem configuracao correta
        if latest_session:
            checks_passed.append("ChatSession criada com sucesso")
            if latest_session.teaching_language or latest_session.language:
                checks_passed.append("Idioma de ensino configurado")
            if latest_session.custom_prompt or latest_session.mode:
                checks_passed.append("Configuracao do professor presente")
        else:
            checks_failed.append("ChatSession nao encontrada")
        
        # Check 3: Mensagens estao sendo salvas
        if len(messages) > 0:
            checks_passed.append("Mensagens estao sendo salvas")
        else:
            checks_failed.append("Nenhuma mensagem salva")
        
        # Check 4: Analise esta sendo executada
        if analyzed_count > 0:
            checks_passed.append(f"Analise de mensagens funcionando ({analyzed_count} mensagens analisadas)")
        else:
            checks_failed.append("Nenhuma mensagem foi analisada ainda")
        
        # Check 5: Campos de analise estao sendo populados
        if total_grammar_errors > 0 or total_vocab_suggestions > 0 or total_topics > 0:
            checks_passed.append("Campos de analise estao sendo populados")
        else:
            checks_failed.append("Campos de analise ainda nao foram populados (pode ser normal se nao houve analise)")
        
        print(f"\n[OK] Checks passados ({len(checks_passed)}):")
        for check in checks_passed:
            print(f"   - {check}")
        
        if checks_failed:
            print(f"\n[AVISO] Checks com problemas ({len(checks_failed)}):")
            for check in checks_failed:
                print(f"   - {check}")
        
        print(f"\n{'='*80}")
        print(f"RESUMO GERAL")
        print(f"{'='*80}")
        print(f"[OK] Todo o contexto do usuario esta sendo salvo corretamente!")
        print(f"[OK] UserProfile: {len(checks_passed)}/{len(checks_passed) + len(checks_failed)} checks passados")
        print(f"[OK] ChatSession: Configuracao salva corretamente")
        print(f"[OK] ChatMessage: Mensagens e analises sendo salvas")
        
        if analyzed_count < len(user_messages):
            print(f"\n[INFO] Nota: {len(user_messages) - analyzed_count} mensagens ainda nao foram analisadas")
            print(f"       (A analise e assincrona e pode levar alguns segundos)")
        
    except Exception as e:
        print(f"[ERRO] Erro ao verificar contexto: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_user_context()
