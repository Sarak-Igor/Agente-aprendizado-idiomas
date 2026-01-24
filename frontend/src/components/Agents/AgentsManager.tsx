import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import agentApi, { AgentResponse } from '../../services/agentService';
import './AgentsManager.css';

const AgentsManager: React.FC = () => {
    const [agents, setAgents] = useState<AgentResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [newAgent, setNewAgent] = useState({
        name: '',
        description: '',
        base_prompt: ''
    });

    const navigate = useNavigate();

    useEffect(() => {
        fetchAgents();
    }, []);

    const fetchAgents = async () => {
        try {
            setLoading(true);
            const data = await agentApi.listAgents();
            setAgents(data);
        } catch (error) {
            console.error('Erro ao buscar agentes:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateAgent = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await agentApi.createAgent(newAgent);
            setIsModalOpen(false);
            setNewAgent({ name: '', description: '', base_prompt: '' });
            fetchAgents();
        } catch (error) {
            console.error('Erro ao criar agente:', error);
        }
    };

    const startSession = async (agentId: string) => {
        try {
            const session = await agentApi.createSession(agentId);
            navigate(`/app/agents/chat/${session.id}`);
        } catch (error) {
            console.error('Erro ao iniciar sessão:', error);
        }
    };

    return (
        <div className="agents-container">
            <div className="agents-header">
                <h1>Agentes Especialistas</h1>
                <button className="btn-create-agent" onClick={() => setIsModalOpen(true)}>
                    + Novo Especialista
                </button>
            </div>

            {loading ? (
                <div className="loading">Carregando especialistas...</div>
            ) : (
                <div className="agents-grid">
                    {agents.length > 0 ? (
                        agents.map((agent) => (
                            <div key={agent.id} className="agent-card">
                                <div>
                                    <h3>{agent.name}</h3>
                                    <p>{agent.description || 'Sem descrição definida.'}</p>
                                </div>
                                <div className="agent-actions">
                                    <button className="btn-chat" onClick={() => startSession(agent.id)}>
                                        Iniciar Chat
                                    </button>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="empty-state">
                            <p>Você ainda não criou nenhum agente especialista.</p>
                            <button className="btn-create-agent" onClick={() => setIsModalOpen(true)}>
                                Crie o seu primeiro agora
                            </button>
                        </div>
                    )}
                </div>
            )}

            {isModalOpen && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <h2>Criar Especialista</h2>
                        <form onSubmit={handleCreateAgent}>
                            <div className="form-group">
                                <label>Nome do Agente</label>
                                <input
                                    type="text"
                                    value={newAgent.name}
                                    onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                                    placeholder="Ex: Tutor de Python, Guia de Viagens Japão..."
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Descrição Curta</label>
                                <input
                                    type="text"
                                    value={newAgent.description}
                                    onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
                                    placeholder="Para que serve este agente?"
                                />
                            </div>
                            <div className="form-group">
                                <label>System Prompt (Personalidade e Regras)</label>
                                <textarea
                                    rows={5}
                                    value={newAgent.base_prompt}
                                    onChange={(e) => setNewAgent({ ...newAgent, base_prompt: e.target.value })}
                                    placeholder="Defina as instruções de como o agente deve se comportar..."
                                    required
                                />
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn-cancel" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                                <button type="submit" className="btn-create-agent">Salvar e Criar</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AgentsManager;
