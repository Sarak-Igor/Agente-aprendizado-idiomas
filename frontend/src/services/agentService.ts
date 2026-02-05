import api from './api';

export interface AgentBase {
    name: string;
    description?: string;
    base_prompt: string;
    configuration?: Record<string, any>;
}

export interface AgentCreate extends AgentBase { }

export interface AgentResponse extends AgentBase {
    id: string;
    user_id: string;
    created_at: string;
}

export interface AgentSessionResponse {
    id: string;
    agent_id: string;
    summary?: string;
    semantic_context: Record<string, any>;
    message_count: number;
    created_at: string;
}

export interface AgentChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
    metadata_json?: Record<string, any>;
}

export interface AgentDocumentResponse {
    id: string;
    status: string;
    file_name: string;
}

export const agentApi = {
    /**
     * Lista todos os agentes do usuário
     */
    listAgents: async (): Promise<AgentResponse[]> => {
        const response = await api.get<AgentResponse[]>('/agents/');
        return response.data;
    },

    /**
     * Lista modelos disponíveis baseados nas chaves do usuário
     */
    getAvailableModels: async (): Promise<any[]> => {
        const response = await api.get('/agents/available-models');
        return response.data.models;
    },

    /**
     * Cria um novo agente especialista
     */
    createAgent: async (agentData: AgentCreate): Promise<AgentResponse> => {
        const response = await api.post<AgentResponse>('/agents/', agentData);
        return response.data;
    },

    /**
     * Obtém detalhes da sessão, incluindo resumo e prompt do agente
     */
    getSession: async (sessionId: string): Promise<any> => {
        const response = await api.get(`/agents/sessions/${sessionId}`);
        return response.data;
    },

    /**
     * Inicia uma nova sessão com um agente
     */
    createSession: async (agentId: string): Promise<AgentSessionResponse> => {
        const response = await api.post<AgentSessionResponse>(`/agents/${agentId}/sessions`);
        return response.data;
    },

    /**
     * Envia uma mensagem para o agente e recebe a resposta
     */
    sendMessage: async (sessionId: string, content: string, model?: string): Promise<AgentChatMessage> => {
        const response = await api.post<AgentChatMessage>(`/agents/sessions/${sessionId}/chat`, {
            content,
            model
        });
        return response.data;
    },

    /**
     * Recupera o histórico de mensagens de uma sessão
     */
    getMessages: async (sessionId: string): Promise<AgentChatMessage[]> => {
        const response = await api.get<AgentChatMessage[]>(`/agents/sessions/${sessionId}/messages`);
        return response.data;
    },

    /**
     * Faz upload de um documento para conhecimento do agente na sessão
     */
    uploadDocument: async (sessionId: string, file: File): Promise<AgentDocumentResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post<AgentDocumentResponse>(
            `/agents/sessions/${sessionId}/documents`,
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            }
        );
        return response.data;
    },
};

export default agentApi;
