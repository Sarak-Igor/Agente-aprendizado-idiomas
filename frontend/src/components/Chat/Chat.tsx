import { useState, useEffect, useRef } from 'react';
import { chatApi, ChatSession, ChatMessage, ChatSessionCreate, AvailableModelsResponse, ChangeModelRequest, UpdateSessionConfigRequest } from '../../services/api';
import { storage } from '../../services/storage';
import './Chat.css';

export const Chat = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModelsResponse>({});
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [changingModel, setChangingModel] = useState(false);
  const [showConfigPopup, setShowConfigPopup] = useState(false);
  const [teachingLanguage, setTeachingLanguage] = useState<string>('en');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [defaultPrompt, setDefaultPrompt] = useState<string>('');

  const targetLanguage = storage.getTargetLanguage();

  // Carrega sessões e inicializa chat automaticamente
  const createNewSession = async () => {
    if (!targetLanguage) {
      console.warn('Idioma de destino não selecionado. Não é possível criar sessão.');
      return;
    }

    setCreatingSession(true);
    try {
      // Usa modo 'conversation' como padrão (mais natural)
      const sessionData: ChatSessionCreate = {
        mode: 'conversation',
        language: targetLanguage,
      };
      const session = await chatApi.createSession(sessionData);
      setCurrentSession(session);
      setSessions([session, ...sessions]);
      setMessages([]);
    } catch (error: any) {
      console.error('Erro ao criar sessão:', error);
      // Não mostra alerta para erro silencioso na inicialização
      if (!currentSession) {
        // Só mostra erro se não houver sessão anterior
        alert(error.response?.data?.detail || 'Erro ao criar sessão de chat');
      }
    } finally {
      setCreatingSession(false);
    }
  };

  // Carrega sessões e inicializa chat automaticamente
  useEffect(() => {
    const initializeChat = async () => {
      // Primeiro carrega sessões existentes
      try {
        const data = await chatApi.listSessions();
        setSessions(data);

        // Se há sessões ativas, usa a mais recente
        const activeSession = data.find(s => s.is_active);
        if (activeSession) {
          setCurrentSession(activeSession);
          return; // Já tem sessão, não precisa criar
        }
      } catch (error: any) {
        console.error('Erro ao carregar sessões:', error);
      }

      // Se não há sessão ativa e tem targetLanguage, cria uma nova
      const lang = storage.getTargetLanguage();
      if (!currentSession && !creatingSession && lang) {
        await createNewSession();
      } else if (!lang) {
        // Se não tem targetLanguage, tenta novamente após delay
        setTimeout(async () => {
          const langRetry = storage.getTargetLanguage();
          if (!currentSession && !creatingSession && langRetry) {
            await createNewSession();
          }
        }, 1000);
      }
    };

    initializeChat();
  }, []); // Executa apenas uma vez ao montar

  useEffect(() => {
    if (currentSession) {
      loadSessionMessages();
      loadAvailableModels();
      // Atualiza valores do popup quando a sessão muda
      const lang = currentSession.teaching_language || currentSession.language || 'en';
      setTeachingLanguage(lang);
      setCustomPrompt(currentSession.custom_prompt || '');
      // Calcula prompt padrão
      setDefaultPrompt(calculateDefaultPrompt(lang, currentSession.mode));
    }
  }, [currentSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Calcula o prompt padrão baseado no idioma e modo
  const calculateDefaultPrompt = (lang: string, mode: string = 'conversation'): string => {
    const languageNames: { [key: string]: string } = {
      'pt': 'português',
      'en': 'inglês',
      'es': 'espanhol',
      'fr': 'francês',
      'de': 'alemão',
      'it': 'italiano',
      'ja': 'japonês',
      'ko': 'coreano',
      'zh': 'chinês',
      'ru': 'russo'
    };

    const learningLanguage = languageNames[lang] || lang;
    const nativeLanguage = 'português';
    const proficiency = 'iniciante';

    if (mode === 'writing') {
      return `Você é um professor de ${learningLanguage} experiente e paciente. Seu aluno é ${proficiency} e fala ${nativeLanguage} como idioma nativo.

MODO: ESCRITA
- Avalie a escrita do aluno
- Corrija erros gramaticais de forma clara e didática
- Explique as correções quando necessário
- Forneça sugestões de vocabulário mais apropriado
- Seja encorajador e positivo
- Use ${nativeLanguage} para explicações quando necessário
- Mantenha o foco em melhorar a escrita do aluno

Comece a conversa de forma amigável e pergunte sobre o que o aluno gostaria de praticar hoje.`;
    } else {
      return `Você é um professor de ${learningLanguage} experiente e paciente. Seu aluno é ${proficiency} e fala ${nativeLanguage} como idioma nativo.

MODO: CONVERSA
- Converse naturalmente em ${learningLanguage}
- Ajuste a complexidade do vocabulário ao nível do aluno (${proficiency})
- Faça perguntas interessantes para manter a conversa fluindo
- Corrija erros de forma sutil e natural
- Use ${nativeLanguage} apenas quando necessário para explicações
- Seja encorajador e crie um ambiente descontraído

Comece a conversa de forma natural e amigável.`;
    }
  };

  const loadSessions = async () => {
    try {
      const data = await chatApi.listSessions();
      setSessions(data);

      // Se não há sessão atual, tenta usar a mais recente ativa
      if (!currentSession && data.length > 0) {
        const activeSession = data.find(s => s.is_active);
        if (activeSession) {
          setCurrentSession(activeSession);
        }
      }
    } catch (error: any) {
      console.error('Erro ao carregar sessões:', error);
      // O ProtectedRoute já gerencia autenticação
    }
  };

  const loadSessionMessages = async () => {
    if (!currentSession) return;

    try {
      const data = await chatApi.getSession(currentSession.id);
      setMessages(data.messages);
      // Atualiza sessão atual com dados mais recentes
      setCurrentSession(data);
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error);
    }
  };

  const loadAvailableModels = async () => {
    try {
      const models = await chatApi.getAvailableModels();
      setAvailableModels(models);
    } catch (error) {
      console.error('Erro ao carregar modelos disponíveis:', error);
    }
  };

  const handleChangeModel = async (service: string, model: string) => {
    if (!currentSession || changingModel) return;

    setChangingModel(true);
    try {
      const updatedSession = await chatApi.changeModel(currentSession.id, { service, model });
      setCurrentSession(updatedSession);
      setShowModelSelector(false);
    } catch (error: any) {
      console.error('Erro ao trocar modelo:', error);
      alert(error.response?.data?.detail || 'Erro ao trocar modelo');
    } finally {
      setChangingModel(false);
    }
  };

  const getModelDisplayName = (session: ChatSession | null): string => {
    if (!session || !session.model_service || !session.model_name) {
      return 'Modelo não definido';
    }

    const serviceNames: { [key: string]: string } = {
      'gemini': 'Gemini',
      'openrouter': 'OpenRouter',
      'groq': 'Groq',
      'together': 'Together'
    };

    const serviceName = serviceNames[session.model_service] || session.model_service;
    return `${serviceName} - ${session.model_name}`;
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentSession || loading) return;

    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      content_type: 'text',
      created_at: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await chatApi.sendMessage(currentSession.id, {
        content: inputMessage,
        content_type: 'text',
      });
      setMessages((prev) => [...prev, response]);
    } catch (error: any) {
      console.error('Erro ao enviar mensagem:', error);
      alert(error.response?.data?.detail || 'Erro ao enviar mensagem');
      // Remove mensagem temporária em caso de erro
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        await sendAudioMessage(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Erro ao iniciar gravação:', error);
      alert('Erro ao acessar o microfone. Verifique as permissões.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendAudioMessage = async (audioBlob: Blob) => {
    if (!currentSession || loading) return;

    setLoading(true);
    try {
      const audioFile = new File([audioBlob], 'audio.webm', { type: 'audio/webm' });
      const response = await chatApi.sendAudio(currentSession.id, audioFile);
      setMessages((prev) => [...prev, response]);
    } catch (error: any) {
      console.error('Erro ao enviar áudio:', error);
      if (error.response?.status !== 501) {
        alert(error.response?.data?.detail || 'Erro ao enviar áudio');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>💬 Chat com Professor</h2>
        <div className="chat-controls">
          {currentSession ? (
            <>
              <button
                onClick={() => {
                  // Carrega valores da sessão ao abrir o popup
                  if (currentSession) {
                    const lang = currentSession.teaching_language || currentSession.language || 'en';
                    setTeachingLanguage(lang);
                    setCustomPrompt(currentSession.custom_prompt || '');
                    setDefaultPrompt(calculateDefaultPrompt(lang, currentSession.mode));
                  }
                  setShowConfigPopup(true);
                }}
                className="btn-config"
                title="Configurações"
              >
                ⚙️
              </button>
              <div className="current-model-info">
                <span className="model-label">Modelo:</span>
                <span className="model-name">{getModelDisplayName(currentSession)}</span>
                <button
                  onClick={() => setShowModelSelector(true)}
                  className="btn-change-model"
                  disabled={changingModel}
                  title="Trocar modelo"
                >
                  🔄
                </button>
              </div>
              <button
                onClick={async () => {
                  setCurrentSession(null);
                  setMessages([]);
                  // Cria nova sessão automaticamente
                  await createNewSession();
                }}
                className="btn-secondary"
              >
                Nova Conversa
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  // Carrega valores da sessão ao abrir o popup
                  if (currentSession) {
                    const lang = currentSession.teaching_language || currentSession.language || 'en';
                    setTeachingLanguage(lang);
                    setCustomPrompt(currentSession.custom_prompt || '');
                    setDefaultPrompt(calculateDefaultPrompt(lang, currentSession.mode));
                  }
                  setShowConfigPopup(true);
                }}
                className="btn-config"
                title="Configurações"
              >
                ⚙️
              </button>
              {creatingSession && (
                <span className="creating-session-indicator">Criando sessão...</span>
              )}
            </>
          )}
        </div>
      </div>

      {!currentSession ? (
        <div className="chat-welcome">
          <p>Inicializando chat...</p>
          {creatingSession && (
            <div className="loading-indicator">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="chat-messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.role}`}
              >
                <div className="message-content">
                  {message.role === 'user' && message.content_type === 'audio' && (
                    <div className="audio-indicator">🎤 Áudio enviado</div>
                  )}
                  <p>{message.content}</p>
                  {message.feedback_type && (
                    <span className="feedback-badge">{message.feedback_type}</span>
                  )}
                  {message.analysis_metadata?.notices && message.analysis_metadata.notices.length > 0 && (
                    <div className="message-notices">
                      {message.analysis_metadata.notices.map((notice, idx) => (
                        <div key={idx} className="notice-item">
                          <span className="notice-icon">⚠️</span>
                          <span className="notice-text">{notice}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="message-time">
                  {new Date(message.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            <div className="chat-input-wrapper">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua mensagem ou use o botão de áudio para gravar..."
                disabled={loading}
                rows={3}
              />
              <div className="chat-input-actions">
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`audio-button ${isRecording ? 'recording' : ''}`}
                  disabled={loading}
                  title={isRecording ? 'Parar gravação' : 'Gravar áudio'}
                >
                  {isRecording ? '⏹️' : '🎤'}
                </button>
                <button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || loading}
                  className="send-button"
                >
                  Enviar
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {showConfigPopup && (
        <div className="config-popup-overlay" onClick={() => setShowConfigPopup(false)}>
          <div className="config-popup-modal" onClick={(e) => e.stopPropagation()}>
            <div className="config-popup-header">
              <h3>Configurações do Professor</h3>
              <button
                className="close-button"
                onClick={() => setShowConfigPopup(false)}
              >
                ×
              </button>
            </div>
            <div className="config-popup-content">
              <div className="config-section">
                <label className="config-label">
                  Idioma que o Professor Ensina:
                </label>
                <select
                  value={teachingLanguage}
                  onChange={(e) => {
                    const lang = e.target.value;
                    setTeachingLanguage(lang);
                    // Atualiza prompt padrão quando o idioma muda
                    if (currentSession && !customPrompt) {
                      setDefaultPrompt(calculateDefaultPrompt(lang, currentSession.mode));
                    }
                  }}
                  className="language-selector"
                >
                  <option value="en">Inglês</option>
                  <option value="pt">Português</option>
                  <option value="es">Espanhol</option>
                  <option value="fr">Francês</option>
                  <option value="de">Alemão</option>
                  <option value="it">Italiano</option>
                  <option value="ja">Japonês</option>
                  <option value="ko">Coreano</option>
                  <option value="zh">Chinês</option>
                  <option value="ru">Russo</option>
                </select>
              </div>
              <div className="config-section">
                <label className="config-label">
                  Prompt do Professor (Personalizado):
                </label>
                <textarea
                  value={customPrompt || defaultPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  className="prompt-textarea"
                  placeholder="Deixe vazio para usar o prompt padrão baseado no idioma selecionado..."
                  rows={10}
                />
                <p className="config-hint">
                  O prompt padrão será usado se este campo estiver vazio. O prompt personalizado substituirá completamente o padrão.
                </p>
              </div>
              <div className="config-popup-actions">
                <button
                  onClick={async () => {
                    if (currentSession) {
                      try {
                        // Se o prompt editado é igual ao padrão, salva como vazio para usar o padrão
                        const promptToSave = (customPrompt && customPrompt.trim() !== defaultPrompt.trim())
                          ? customPrompt.trim()
                          : undefined;

                        await chatApi.updateConfig(currentSession.id, {
                          teaching_language: teachingLanguage,
                          custom_prompt: promptToSave
                        });
                        setShowConfigPopup(false);
                        // Recarrega a sessão para atualizar
                        loadSessionMessages();
                      } catch (error: any) {
                        console.error('Erro ao salvar configurações:', error);
                        alert(error.response?.data?.detail || 'Erro ao salvar configurações');
                      }
                    } else {
                      // Se não há sessão, apenas fecha o popup (configurações serão aplicadas na próxima sessão)
                      setShowConfigPopup(false);
                    }
                  }}
                  className="btn-primary"
                >
                  Salvar
                </button>
                <button
                  onClick={() => {
                    setShowConfigPopup(false);
                    // Reseta para os valores da sessão ao cancelar
                    if (currentSession) {
                      const lang = currentSession.teaching_language || currentSession.language || 'en';
                      setTeachingLanguage(lang);
                      setCustomPrompt(currentSession.custom_prompt || '');
                      setDefaultPrompt(calculateDefaultPrompt(lang, currentSession.mode));
                    }
                  }}
                  className="btn-secondary"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showModelSelector && (
        <div className="model-selector-overlay" onClick={() => setShowModelSelector(false)}>
          <div className="model-selector-modal" onClick={(e) => e.stopPropagation()}>
            <div className="model-selector-header">
              <h3>Selecionar Modelo</h3>
              <button
                className="close-button"
                onClick={() => setShowModelSelector(false)}
              >
                ×
              </button>
            </div>
            <div className="model-selector-content">
              {Object.entries(availableModels).map(([service, models]) => {
                if (!models || models.length === 0) return null;

                const serviceNames: { [key: string]: string } = {
                  'gemini': 'Gemini',
                  'openrouter': 'OpenRouter',
                  'groq': 'Groq',
                  'together': 'Together'
                };

                const serviceIcons: { [key: string]: string } = {
                  'gemini': '🤖',
                  'openrouter': '🌐',
                  'groq': '⚡',
                  'together': '🔗'
                };

                return (
                  <div key={service} className="model-service-group">
                    <div className="service-header">
                      <span className="service-icon">{serviceIcons[service] || '🔧'}</span>
                      <h4 className={`service-name service-${service}`}>
                        {serviceNames[service] || service}
                      </h4>
                      <span className="service-badge">API</span>
                    </div>
                    <div className="model-list">
                      {models.map((model) => (
                        <button
                          key={model.name}
                          className={`model-item ${currentSession?.model_service === service &&
                              currentSession?.model_name === model.name
                              ? 'active'
                              : ''
                            } ${!model.available ? 'unavailable' : ''}`}
                          onClick={() => handleChangeModel(service, model.name)}
                          disabled={changingModel || !model.available}
                        >
                          <div className="model-item-content">
                            <span className="model-item-name">{model.name}</span>
                            {model.category && (
                              <span className="model-category">{model.category}</span>
                            )}
                          </div>
                          <div className="model-item-badges">
                            {currentSession?.model_service === service &&
                              currentSession?.model_name === model.name && (
                                <span className="model-item-badge current">Atual</span>
                              )}
                            {!model.available && (
                              <span className="model-item-badge unavailable">Indisponível</span>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
              {Object.keys(availableModels).length === 0 && (
                <div className="no-models">Carregando modelos disponíveis...</div>
              )}
            </div>
            {changingModel && (
              <div className="model-selector-loading">Trocando modelo...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
