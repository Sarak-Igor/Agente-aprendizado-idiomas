import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import agentApi, { AgentChatMessage, AgentDocumentResponse } from '../../services/agentService';
import ReactMarkdown from 'react-markdown';
import './AgentChatView.css';

const AgentChatView: React.FC = () => {
    const { sessionId } = useParams<{ sessionId: string }>();
    const [session, setSession] = useState<any | null>(null);
    const [messages, setMessages] = useState<AgentChatMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [sending, setSending] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [documents, setDocuments] = useState<AgentDocumentResponse[]>([]);
    const [availableModels, setAvailableModels] = useState<any[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>('');
    const [isHelpOpen, setIsHelpOpen] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();

    useEffect(() => {
        if (sessionId) {
            loadData();
            // Polling para atualizar o resumo a cada 10 segundos
            const interval = setInterval(refreshSession, 10000);
            return () => clearInterval(interval);
        }
    }, [sessionId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const loadData = async () => {
        if (!sessionId) return;
        try {
            const [history, sessionData, models] = await Promise.all([
                agentApi.getMessages(sessionId),
                agentApi.getSession(sessionId),
                agentApi.getAvailableModels()
            ]);
            setMessages(history);
            setSession(sessionData);
            setAvailableModels(models);

            // Tenta manter o modelo atual da sessão ou o configurado no Agente
            if (!selectedModel) {
                const configModel = sessionData?.agent?.configuration?.model;
                const defaultModel = configModel || models.find((m: any) => m.tier === 'free')?.id || models[0]?.id || '';
                setSelectedModel(defaultModel);
            }
        } catch (error) {
            console.error('Erro ao carregar chat:', error);
        }
    };

    const refreshSession = async () => {
        if (!sessionId) return;
        try {
            const sessionData = await agentApi.getSession(sessionId);
            setSession(sessionData);
        } catch (error) {
            console.error('Erro ao atualizar sessão:', error);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputText.trim() || !sessionId || sending) return;

        const userMsg: AgentChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: inputText,
            created_at: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMsg]);
        setInputText('');
        setSending(true);

        try {
            const response = await agentApi.sendMessage(sessionId, userMsg.content, selectedModel);
            setMessages(prev => [...prev, response]);
            refreshSession();
        } catch (error: any) {
            console.error('Erro ao enviar mensagem:', error);
            const errorMsg = error.response?.data?.detail || 'Erro ao processar mensagem.';

            setMessages(prev => [...prev, {
                id: `error-${Date.now()}`,
                role: 'system',
                content: `⚠️ Erro: ${errorMsg}`,
                created_at: new Date().toISOString()
            }]);
        } finally {
            setSending(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !sessionId) return;

        setUploading(true);
        try {
            const doc = await agentApi.uploadDocument(sessionId, file);
            setDocuments(prev => [...prev, doc]);

            // Adiciona notificação no chat
            setMessages(prev => [...prev, {
                id: `upload-${Date.now()}`,
                role: 'system',
                content: `📎 Arquivo "${file.name}" adicionado ao meu conhecimento.`,
                created_at: new Date().toISOString()
            }]);
        } catch (error) {
            console.error('Erro no upload:', error);
            alert('Falha ao enviar documento.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="agent-chat-layout">
            {/* Main Chat Area */}
            <div className="chat-main-area">
                <div className="chat-header">
                    <button className="btn-back" onClick={() => navigate('/app/agents')}>← Voltar</button>
                    <span>{session?.agent?.name || 'Sessão de Especialista'}</span>
                    <button className="btn-help" onClick={() => setIsHelpOpen(true)}>❓ Ajuda & Info</button>
                </div>

                <div className="chat-messages">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`message-container ${msg.role}`}>
                            <div className={`message-bubble ${msg.role}`}>
                                {msg.role === 'assistant' ? (
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                ) : (
                                    msg.content
                                )}
                            </div>
                            {msg.role === 'assistant' && msg.metadata_json?.model && (
                                <span className="model-badge">{msg.metadata_json.model}</span>
                            )}
                        </div>
                    ))}
                    {sending && <div className="message-bubble assistant loading">Digitando...</div>}
                    <div ref={messagesEndRef} />
                </div>

                <div className="chat-input-area">
                    <div className="model-selector-container">
                        <select
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="model-dropdown"
                        >
                            <option value="">Configuração do Agente (Padrão)</option>
                            {availableModels.map(m => (
                                <option key={m.id} value={m.id}>
                                    [{m.service.toUpperCase()}] {m.name} {m.tier === 'free' ? '(Grátis)' : ''}
                                </option>
                            ))}
                        </select>
                    </div>
                    <form onSubmit={handleSendMessage} className="input-wrapper">
                        <label className="btn-attach" title="Anexar documento ao conhecimento">
                            📎
                            <input type="file" hidden onChange={handleFileUpload} accept=".pdf,.txt,.json,.md" />
                        </label>
                        <input
                            type="text"
                            placeholder="Pergunte qualquer coisa ao seu especialista..."
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            disabled={sending}
                        />
                        <button type="submit" className="btn-send" disabled={sending || !inputText.trim()}>
                            Enviar
                        </button>
                    </form>
                </div>
            </div>

            {/* Persistence & Knowledge Sidebar */}
            <div className="knowledge-sidebar">
                <div className="knowledge-section">
                    <h4>Memória Semântica (Long Term)</h4>
                    <div className="memory-box">
                        {session?.summary || "O agente ainda está construindo um resumo da sua conversa..."}
                    </div>
                </div>

                <div className="knowledge-section">
                    <h4>Conhecimento Externo (RAG)</h4>
                    <label className="file-upload-zone">
                        <input type="file" hidden onChange={handleFileUpload} accept=".pdf,.txt,.json,.md" />
                        {uploading ? <span>Processando...</span> : (
                            <>
                                <strong>+ Adicionar Documento</strong>
                                <br />
                                <span>PDF, TXT, JSON, MD</span>
                            </>
                        )}
                    </label>

                    <div className="document-list" style={{ marginTop: '1rem' }}>
                        {documents.map(doc => (
                            <div key={doc.id} className="document-item">
                                <div className={`document-status ${doc.status}`}></div>
                                <span>{doc.file_name}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Modal de Ajuda e Info */}
            {isHelpOpen && (
                <div className="modal-overlay">
                    <div className="modal-content help-modal">
                        <h2>Como funciona este Agente?</h2>

                        <div className="help-section">
                            <h3>🧠 Memória de Longo Prazo</h3>
                            <p>O agente resume automaticamente a conversa a cada 5 mensagens. Esse resumo é visualizado na barra lateral e ajuda o agente a não "se perder" em conversas longas.</p>
                        </div>

                        <div className="help-section">
                            <h3>📂 Conhecimento (RAG)</h3>
                            <p>Ao subir arquivos (PDF, JSON, MD), o agente passa a consultar esses documentos antes de responder.
                                <strong>Exemplo:</strong> Suba o manual de um produto e pergunte "Como configuro o Wi-Fi?".</p>
                        </div>

                        <div className="help-section prompt-view">
                            <h3>📜 Prompt Base do Agente</h3>
                            <p>Instruções fundamentais que definem a personalidade:</p>
                            <pre>{session?.agent?.base_prompt}</pre>
                        </div>

                        <div className="modal-footer">
                            <button className="btn-create-agent" onClick={() => setIsHelpOpen(false)}>Entendi!</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AgentChatView;
