import React, { useState, useEffect } from 'react';
import './MCPFactory.css';
import axios from 'axios';

interface MCPTool {
    id: string;
    name: string;
    display_name: string;
    category: string;
    description: string;
    runtime: string;
    config_schema: any;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface FlowNode {
    id: string;
    type: 'trigger' | 'brain' | 'tool' | 'logic' | 'wait';
    label: string;
    icon: string;
    position: { x: number; y: number };
    data: any;
}

interface FlowEdge {
    id: string;
    source: string;
    target: string;
}

interface AgentBlueprint {
    name: string;
    version: string;
    description: string;
    nodes: FlowNode[];
    edges: FlowEdge[];
    settings: {
        brain_model: string;
        temperature: number;
        memory_type: string;
        context_window: number;
    };
    resilience: {
        retries: number;
        human_approval: boolean;
    };
}

export const MCPFactory: React.FC = () => {
    const [tools, setTools] = useState<MCPTool[]>([]);
    const [activeCategory, setActiveCategory] = useState<string | null>(null);
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [availableModels, setAvailableModels] = useState<any[]>([]);
    const [isCustomModel, setIsCustomModel] = useState(false);
    const [selectedModel, setSelectedModel] = useState("google/gemini-2.0-flash-exp:free");
    const [isLoading, setIsLoading] = useState(false);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [isSecretsModalOpen, setIsSecretsModalOpen] = useState(false);
    const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const [activeConfigTab, setActiveConfigTab] = useState<'basic' | 'intelligence' | 'operation'>('basic');
    const [connectingNodeId, setConnectingNodeId] = useState<string | null>(null);
    const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
    const [toolSearch, setToolSearch] = useState('');

    // Estado do Blueprint (O Workflow sendo montado)
    const [blueprint, setBlueprint] = useState<AgentBlueprint>({
        name: "Automação Inteligente",
        version: "1.0.0",
        description: "Workflow sequencial com IA.",
        nodes: [
            {
                id: 'node-0',
                type: 'trigger',
                label: 'Gatilho (Webhook)',
                icon: '⚡',
                position: { x: 50, y: 150 },
                data: { type: 'webhook' }
            }
        ],
        edges: [],
        settings: {
            brain_model: "openai/gpt-4o",
            temperature: 0.7,
            memory_type: 'short-term',
            context_window: 10
        },
        resilience: {
            retries: 3,
            human_approval: false
        }
    });

    const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

    useEffect(() => {
        const initFactory = async () => {
            await fetchTools();
            await fetchModels();
        };
        initFactory();
    }, []);

    const fetchModels = async () => {
        try {
            const response = await axios.get(`${API_BASE}/agents/available-models`);
            if (response.data.models && response.data.models.length > 0) {
                setAvailableModels(response.data.models);
            } else {
                // Fallback models se o backend não tiver chaves
                setAvailableModels([
                    { id: "google/gemini-2.0-flash-exp:free", name: "Gemini 2.0 Flash (Free)", service: "google", recommended: true },
                    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", service: "anthropic", recommended: true },
                    { id: "openai/gpt-4o", name: "GPT-4o", service: "openai", recommended: true },
                    { id: "meta-llama/llama-3.1-405b", name: "Llama 3.1 405B", service: "meta" },
                    { id: "mistralai/pixtral-12b", name: "Pixtral 12B", service: "mistral" }
                ]);
            }
        } catch (error) {
            console.error('Erro ao buscar modelos:', error);
        }
    };

    const fetchTools = async () => {
        try {
            // Sempre tenta rodar o seed para garantir que o catálogo do banco bata com o código
            await axios.post(`${API_BASE}/mcp/tools/seed`);

            const response = await axios.get(`${API_BASE}/mcp/tools`);
            setTools(response.data);
        } catch (error) {
            console.error('Erro ao buscar ferramentas:', error);
        }
    };

    const templates = [
        {
            id: 'support',
            name: 'Chatbot de Atendimento',
            icon: '💬',
            description: 'Focado em responder clientes e salvar logs.',
            tools: ['mcp-server-google-sheets', 'mcp-server-slack']
        },
        {
            id: 'web',
            name: 'Agente de Pesquisa Web',
            icon: '🌐',
            description: 'Especialista em busca profunda e síntese.',
            tools: ['firecrawl', 'mcp-server-puppeteer']
        },
        {
            id: 'finance',
            name: 'Analista Financeiro',
            icon: '💰',
            description: 'Monitora mercado e gera relatórios.',
            tools: ['binance-mcp', 'mcp-server-notion']
        }
    ];

    const removeEdge = (edgeId: string) => {
        setBlueprint(prev => ({
            ...prev,
            edges: prev.edges.filter(e => e.id !== edgeId)
        }));
    };

    const exportBlueprint = () => {
        // Converter para formato n8n
        const n8nBlueprint = {
            nodes: blueprint.nodes.map(node => ({
                id: node.id,
                name: node.label,
                type: `n8n-nodes-base.${node.type === 'trigger' ? 'webhook' : node.type === 'brain' ? 'aiAgent' : 'httpRequest'}`,
                typeVersion: 1,
                position: [node.position.x, node.position.y],
                parameters: node.data
            })),
            connections: blueprint.edges.reduce((acc: any, edge) => {
                const source = blueprint.nodes.find(n => n.id === edge.source);
                const target = blueprint.nodes.find(n => n.id === edge.target);
                if (source && target) {
                    if (!acc[source.label]) acc[source.label] = { main: [[]] };
                    acc[source.label].main[0].push({
                        node: target.label,
                        type: 'main',
                        index: 0
                    });
                }
                return acc;
            }, {}),
            settings: blueprint.settings,
            meta: {
                name: blueprint.name,
                version: blueprint.version
            }
        };

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(n8nBlueprint, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `${blueprint.name.toLowerCase().replace(/ /g, '_')}_n8n.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Blueprint exportado no formato n8n.`]);
    };

    const addLogicNode = () => {
        const newNode: FlowNode = {
            id: `node-${Date.now()}`,
            type: 'logic',
            label: 'IF/ELSE Lógica',
            icon: '⚖️',
            position: { x: 350, y: 250 },
            data: { condition: '{{result}} === "ok"' }
        };
        setBlueprint(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    };

    const applyTemplate = (template: any) => {
        const selectedTools = tools.filter(t => template.tools.includes(t.name));
        const newNodes: FlowNode[] = [
            { id: 'node-0', type: 'trigger', label: 'Gatilho', icon: '⚡', position: { x: 50, y: 150 }, data: { type: 'webhook' } },
            { id: 'node-1', type: 'brain', label: template.id === 'finance' ? 'Analista Sênior' : 'Assistente IA', icon: '🧠', position: { x: 250, y: 150 }, data: { prompt: '' } }
        ];

        selectedTools.forEach((tool, i) => {
            newNodes.push({
                id: `node-tool-${i}`,
                type: 'tool',
                label: tool.display_name,
                icon: '🛠️',
                position: { x: 450 + (i * 200), y: 150 },
                data: tool
            });
        });

        setBlueprint({
            ...blueprint,
            name: template.name,
            description: template.description,
            nodes: newNodes,
            edges: newNodes.slice(0, -1).map((n, i) => ({
                id: `edge-${i}`,
                source: n.id,
                target: newNodes[i + 1].id
            }))
        });
    };

    const addToolToFlow = (tool: MCPTool) => {
        const newNode: FlowNode = {
            id: `node-${Date.now()}`,
            type: 'tool',
            label: tool.display_name,
            icon: '🛠️',
            position: { x: 250, y: 150 },
            data: tool
        };
        setBlueprint(prev => ({
            ...prev,
            nodes: [...prev.nodes, newNode]
        }));
    };

    const addBrainNode = () => {
        const newNode: FlowNode = {
            id: `node-${Date.now()}`,
            type: 'brain',
            label: 'Cérebro (IA)',
            icon: '🧠',
            position: { x: 450, y: 150 },
            data: {}
        };
        setBlueprint(prev => ({
            ...prev,
            nodes: [...prev.nodes, newNode]
        }));
    };

    const addWaitNode = () => {
        const newNode: FlowNode = {
            id: `node-${Date.now()}`,
            type: 'wait',
            label: 'Aguardar 24h',
            icon: '⏳',
            position: { x: 550, y: 250 },
            data: { delay: '24h' }
        };
        setBlueprint(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    };

    const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
        const node = blueprint.nodes.find(n => n.id === nodeId);
        if (node) {
            setDraggingNodeId(nodeId);
            setDragOffset({
                x: e.clientX - node.position.x,
                y: e.clientY - node.position.y
            });
        }
    };

    const handleCanvasMouseMove = (e: React.MouseEvent) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        setMousePosition({ x, y });

        if (draggingNodeId) {
            const newX = e.clientX - dragOffset.x;
            const newY = e.clientY - dragOffset.y;

            setBlueprint(prev => ({
                ...prev,
                nodes: prev.nodes.map(n => n.id === draggingNodeId ? { ...n, position: { x: newX, y: newY } } : n)
            }));
        }
    };

    const handleCanvasMouseUp = () => {
        setDraggingNodeId(null);
    };

    const handleNodeClick = (nodeId: string) => {
        if (connectingNodeId) {
            if (connectingNodeId !== nodeId) {
                // Evitar duplicatas
                if (!blueprint.edges.find(e => e.source === connectingNodeId && e.target === nodeId)) {
                    const newEdge: FlowEdge = {
                        id: `edge-${Date.now()}`,
                        source: connectingNodeId,
                        target: nodeId
                    };
                    setBlueprint(prev => ({ ...prev, edges: [...prev.edges, newEdge] }));
                }
            }
            setConnectingNodeId(null);
        } else {
            setSelectedNodeId(nodeId);
        }
    };

    const startConnection = (e: React.MouseEvent, nodeId: string) => {
        e.stopPropagation();
        setConnectingNodeId(nodeId);
    };

    const removeNode = (nodeId: string) => {
        setBlueprint(prev => ({
            ...prev,
            nodes: prev.nodes.filter(n => n.id !== nodeId),
            edges: prev.edges.filter(e => e.source !== nodeId && e.target !== nodeId)
        }));
    };

    const clearSelection = () => {
        setSelectedNodeId(null);
        setConnectingNodeId(null);
    };

    const processAssistantResponse = (responseContent: string) => {
        try {
            // Tenta dar parse no JSON retornado pela LLM
            const parsed = JSON.parse(responseContent);

            if (parsed.text) {
                setChatHistory(prev => [...prev, { role: 'assistant', content: parsed.text }]);
            }

            if (parsed.actions && Array.isArray(parsed.actions)) {
                parsed.actions.forEach((action: any) => {
                    executeAssistantAction(action);
                });
            }
        } catch (e) {
            // Se falhar o parse, trata como texto puro (fallback)
            setChatHistory(prev => [...prev, { role: 'assistant', content: responseContent }]);
        }
    };

    const executeAssistantAction = (action: any) => {
        console.log("Executando ação do assistente:", action);

        switch (action.type) {
            case 'ADD_NODE':
                const nodeData = action.node;
                const newNode: FlowNode = {
                    id: nodeData.id || `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    type: nodeData.type || 'brain',
                    label: nodeData.label || 'Novo Nó',
                    icon: nodeData.type === 'trigger' ? '⚡' :
                        nodeData.type === 'brain' ? '🧠' :
                            nodeData.type === 'tool' ? '🛠️' :
                                nodeData.type === 'logic' ? '⚖️' : '⏳',
                    position: nodeData.position || { x: 400, y: 300 },
                    data: nodeData.data || {}
                };
                setBlueprint(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }));
                setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Assistente adicionou nó: ${newNode.label}`]);
                break;

            case 'CONNECT':
                if (action.from && action.to) {
                    const newEdge: FlowEdge = {
                        id: `edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                        source: action.from,
                        target: action.to
                    };
                    setBlueprint(prev => ({ ...prev, edges: [...prev.edges, newEdge] }));
                    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Assistente criou conexão entre nós.`]);
                }
                break;

            case 'INSTALL_TOOL':
                setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Assistente solicitou instalação da ferramenta: ${action.tool}`]);
                // TODO: Chamar endpoint de instalação se necessário
                break;

            default:
                console.warn("Ação desconhecida:", action.type);
        }
    };

    const handleSendMessage = async () => {
        if (!inputValue.trim()) return;

        const newMessage: ChatMessage = { role: 'user', content: inputValue };
        const updatedHistory = [...chatHistory, newMessage];
        setChatHistory(updatedHistory);
        setInputValue('');
        setIsLoading(true);

        try {
            const response = await axios.post(`${API_BASE}/mcp/assistant/chat`, {
                message: inputValue,
                history: chatHistory,
                model_name: selectedModel,
                blueprint: blueprint
            });

            // Se for string de erro amigável, não tenta fazer parse JSON
            let responseData;
            try {
                responseData = typeof response.data.response === 'string' ? JSON.parse(response.data.response) : response.data.response;
            } catch {
                responseData = { text: response.data.response, actions: [] };
            }

            processAssistantResponse(responseData);
        } catch (error: any) {
            console.error('Erro no assistente:', error);
            const errorMsg = error.response?.data?.detail || error.message;
            setChatHistory(prev => [...prev, {
                role: 'assistant',
                content: `Erro: O assistente não pôde processar seu pedido (${errorMsg}). Verifique se seu backend está rodando e se as chaves de API estão configuradas corretamente.`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const runTest = async () => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] 🚀 Iniciando execução REAL do Agente...`]);

        try {
            setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Salvando definição do fluxo...`]);

            // Usamos um ID especial para testes rápidos de playground
            const testAgentId = "test-playground-agent";

            // 1. Salva o blueprint temporariamente no backend
            await axios.post(`${API_BASE}/agents/test-playground-agent/blueprint`, blueprint);

            setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Ativando Motor de Execução...`]);

            // 2. Executa o Motor
            const runResponse = await axios.post(`${API_BASE}/agents/test-playground-agent/run`, {
                input_data: { message: "Input de teste" }
            });

            if (runResponse.data.status === 'completed') {
                const result = runResponse.data.result;
                setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ✅ Execução concluída!`]);

                // Exibe logs de cada nó percorrido
                result.history.forEach((step: any) => {
                    setLogs(prev => [...prev, `[${step.timestamp}] Nó ${step.node_id} (${step.type}): Processado.`]);
                });

                if (result.error) {
                    setLogs(prev => [...prev, `[❌ ERRO]: ${result.error}`]);
                }
            }
        } catch (error: any) {
            const errorMsg = error.response?.data?.detail || error.message;
            setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ❌ Erro na execução: ${errorMsg}`]);
        }
    };

    const handleImportN8N = () => {
        setIsImportModalOpen(true);
    };

    const categories = Array.from(new Set(tools.map(t => t.category)));

    return (
        <div className="mcp-factory-container">
            <div className="mcp-factory-header">
                <div className="title-area">
                    <h1>🏗️ Fábrica de Agentes MCP</h1>
                    <p>Crie especialistas sob demanda integrados ao seu ecossistema.</p>
                </div>
                <div className="assistant-settings">
                    <label>Copiloto:</label>
                    <div className="model-selector-wrapper">
                        {!isCustomModel ? (
                            <select
                                value={selectedModel}
                                onChange={(e) => {
                                    if (e.target.value === "custom") {
                                        setIsCustomModel(true);
                                    } else {
                                        setSelectedModel(e.target.value);
                                    }
                                }}
                            >
                                <optgroup label="Recomendados">
                                    {availableModels.filter(m => m.recommended || m.service === 'google').map(m => (
                                        <option key={m.id} value={m.id}>{m.name}</option>
                                    ))}
                                </optgroup>
                                <optgroup label="Todos os Modelos">
                                    {availableModels.filter(m => !m.recommended && m.service !== 'google').map(m => (
                                        <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                    ))}
                                </optgroup>
                                <option value="custom">➕ Digitar modelo customizado...</option>
                            </select>
                        ) : (
                            <div className="custom-model-input">
                                <input
                                    type="text"
                                    placeholder="ID do Modelo (ex: deepseek/coder)"
                                    value={selectedModel}
                                    onChange={(e) => setSelectedModel(e.target.value)}
                                    autoFocus
                                />
                                <button title="Voltar para lista" onClick={() => setIsCustomModel(false)}>✕</button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="utility-bar">
                <button className="btn-utility" onClick={handleImportN8N}>
                    📂 Importar n8n
                </button>
                <button className="btn-utility" onClick={exportBlueprint}>📤 Exportar JSON</button>
                <button className="btn-utility" onClick={() => alert('Link de partilha copiado!')}>🔗 Partilhar</button>
                <button className="btn-utility">⚙️ Config Globlal</button>
            </div>

            <div className="templates-bar">
                <h3>Templates de Agentes:</h3>
                <div className="template-list">
                    {templates.map(t => (
                        <button key={t.id} className="template-card" onClick={() => applyTemplate(t)}>
                            <span className="template-icon">{t.icon}</span>
                            <div className="template-info">
                                <strong>{t.name}</strong>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            <div className="mcp-factory-content">
                {/* Coluna 1: Chat Copiloto */}
                <div className="assistant-section">
                    <div className="chat-window">
                        <div className="chat-header">
                            <span className="ai-badge">IA ASSISTANT</span>
                            <div className="infra-nodes">
                                <div className="infra-badge brain">🧠 {blueprint.settings.brain_model.split('/')[1] || blueprint.settings.brain_model}</div>
                                <div className="infra-badge memory">💾 {blueprint.settings.memory_type}</div>
                            </div>
                        </div>

                        <div className="chat-messages">
                            <div className="message-bubble assistant">
                                Olá! Sou seu arquiteto de agentes. Como posso te ajudar a montar seu especialista hoje?
                            </div>
                            {chatHistory.map((msg, i) => (
                                <div key={i} className={`message-bubble ${msg.role}`}>
                                    {msg.content}
                                </div>
                            ))}
                            {isLoading && <div className="message-bubble assistant loading">Pensando...</div>}
                        </div>

                        <div className="chat-input-area">
                            <input
                                type="text"
                                placeholder="Peça ajuda para configurar..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                            />
                            <button disabled={isLoading} onClick={handleSendMessage}>Enviar</button>
                        </div>
                    </div>
                </div>

                {/* Coluna 2: Canvas do Agente */}
                <div className="canvas-section">
                    <div className="canvas-main">
                        <div className="canvas-header">
                            <div className="blueprint-name">
                                <input
                                    type="text"
                                    value={blueprint.name}
                                    onChange={(e) => setBlueprint({ ...blueprint, name: e.target.value })}
                                />
                            </div>
                            <div className="canvas-actions">
                                <button className="btn-secondary" onClick={() => setBlueprint({
                                    name: "Automação",
                                    version: "1.0.0",
                                    description: "Workflow sequencial com IA.",
                                    nodes: [
                                        { id: 'node-0', type: 'trigger', label: 'Gatilho de Entrada', icon: '⚡', position: { x: 50, y: 150 }, data: { type: 'webhook' } }
                                    ],
                                    edges: [],
                                    settings: {
                                        brain_model: "openai/gpt-4o",
                                        temperature: 0.7,
                                        memory_type: 'short-term',
                                        context_window: 10
                                    },
                                    resilience: { retries: 3, human_approval: false }
                                })}>Limpar</button>
                                <button className="btn-primary" onClick={() => setIsVersionModalOpen(true)}>🚀 Publicar V{blueprint.version}</button>
                            </div>
                        </div>

                        <div
                            className="diagram-canvas agent-flow-canvas"
                            onMouseMove={handleCanvasMouseMove}
                            onMouseUp={handleCanvasMouseUp}
                            onMouseLeave={handleCanvasMouseUp}
                            onClick={clearSelection}
                        >
                            {/*SVG para Edges */}
                            <svg className="flow-lines">
                                {blueprint.edges.map(edge => {
                                    const sourceNode = blueprint.nodes.find(n => n.id === edge.source);
                                    const targetNode = blueprint.nodes.find(n => n.id === edge.target);
                                    if (!sourceNode || !targetNode) return null;

                                    // Cálculo de curva Bezier para as conexões (ajustado para largura 180px)
                                    const x1 = sourceNode.position.x + 180;
                                    const y1 = sourceNode.position.y + 45;
                                    const x2 = targetNode.position.x;
                                    const y2 = targetNode.position.y + 45;
                                    const dx = Math.abs(x2 - x1) * 0.5;

                                    // Ponto médio para o botão de deletar
                                    const midX = x1 + (x2 - x1) / 2;
                                    const midY = y1 + (y2 - y1) / 2;

                                    return (
                                        <g key={edge.id} className="workflow-edge-group">
                                            <path
                                                d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`}
                                                fill="transparent"
                                                stroke="#3b82f6"
                                                strokeWidth="2"
                                                strokeDasharray="5,5"
                                                className="workflow-edge-path"
                                            />
                                            <circle cx={x2} cy={y2} r="4" fill="#3b82f6" />
                                            <g className="edge-delete-btn" onClick={(e) => { e.stopPropagation(); removeEdge(edge.id); }} style={{ cursor: 'pointer' }}>
                                                <circle cx={midX} cy={midY} r="8" fill="#ef4444" />
                                                <text x={midX} y={midY} textAnchor="middle" dy=".3em" fill="white" fontSize="12px" style={{ pointerEvents: 'none' }}>×</text>
                                            </g>
                                        </g>
                                    );
                                })}

                                {connectingNodeId && (
                                    <path
                                        d={`M ${(blueprint.nodes.find(n => n.id === connectingNodeId)?.position.x || 0) + 180} ${(blueprint.nodes.find(n => n.id === connectingNodeId)?.position.y || 0) + 45} L ${mousePosition.x} ${mousePosition.y}`}
                                        fill="transparent"
                                        stroke="#fbbf24"
                                        strokeWidth="3"
                                        strokeDasharray="5,5"
                                        style={{ pointerEvents: 'none' }}
                                    />
                                )}
                            </svg>

                            {blueprint.nodes.map((node) => (
                                <div
                                    key={node.id}
                                    className={`flow-node ${node.type} ${selectedNodeId === node.id ? 'active' : ''} ${connectingNodeId === node.id ? 'connecting' : ''}`}
                                    style={{
                                        left: `${node.position.x}px`,
                                        top: `${node.position.y}px`,
                                        cursor: draggingNodeId === node.id ? 'grabbing' : 'grab'
                                    }}
                                    onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                                    onClick={(e) => { e.stopPropagation(); handleNodeClick(node.id); }}
                                >
                                    <button className="remove-node" onClick={(e) => { e.stopPropagation(); removeNode(node.id); }}>×</button>

                                    <div className="node-content">
                                        <div className="node-main-info">
                                            <div className="node-icon">{node.icon}</div>
                                            <div className="node-text">
                                                <span className="node-label">{node.label}</span>
                                                {node.type === 'brain' && (
                                                    <div className="node-sub-badges">
                                                        <span className="inner-badge">🧠 IA</span>
                                                        <span className="inner-badge">💾 MEM</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div
                                        className="node-handle right"
                                        onMouseDown={(e) => e.stopPropagation()}
                                        onClick={(e) => startConnection(e, node.id)}
                                        title="Ligar ponto"
                                    />
                                    <div
                                        className="node-handle left"
                                        onMouseDown={(e) => e.stopPropagation()}
                                        onClick={(e) => { e.stopPropagation(); handleNodeClick(node.id); }}
                                        title="Ponto de entrada"
                                    />
                                </div>
                            ))}

                            {blueprint.nodes.length === 0 && (
                                <div className="canvas-hint">Adicione <button onClick={addBrainNode}>Cérebro</button> ou ferramentas para iniciar.</div>
                            )}

                            <div className="canvas-controls" style={{ position: 'absolute', bottom: '20px', left: '20px', display: 'flex', gap: '8px' }}>
                                <button className="btn-utility" onClick={addBrainNode}>+ 🧠 Agente (Cérebro+Mem)</button>
                                <button className="btn-utility" onClick={addLogicNode}>+ ⚖️ Lógica</button>
                                <button className="btn-utility" onClick={addWaitNode}>+ ⏳ Espera</button>
                            </div>
                        </div>

                        <div className="tool-catalogue">
                            <div className="tool-catalogue-header">
                                <h3>Ferramentas Disponíveis</h3>
                                <div className="tool-search-box">
                                    <input
                                        type="text"
                                        placeholder="Buscar ferramenta (ex: Gmail, Slack...)"
                                        value={toolSearch}
                                        onChange={(e) => setToolSearch(e.target.value)}
                                    />
                                </div>
                            </div>
                            <div className="category-accordion">
                                {categories.filter(cat => {
                                    if (!toolSearch) return true;
                                    return tools.some(t => t.category === cat && t.display_name.toLowerCase().includes(toolSearch.toLowerCase()));
                                }).map(cat => (
                                    <div key={cat} className="category-item">
                                        <div
                                            className={`category-trigger ${activeCategory === cat || toolSearch ? 'active' : ''}`}
                                            onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
                                        >
                                            <span>{cat}</span>
                                            <span className="chevron">{activeCategory === cat || toolSearch ? '▼' : '▶'}</span>
                                        </div>
                                        {(activeCategory === cat || toolSearch) && (
                                            <div className="tool-grid">
                                                {tools.filter(t => t.category === cat && t.display_name.toLowerCase().includes(toolSearch.toLowerCase())).map(tool => (
                                                    <div key={tool.id} className="tool-item">
                                                        <div className="tool-meta">
                                                            <strong>{tool.display_name}</strong>
                                                            <p>{tool.description.substring(0, 40)}...</p>
                                                        </div>
                                                        <button className="btn-add-tool" onClick={() => addToolToFlow(tool)}>
                                                            {blueprint.nodes.find(n => n.type === 'tool' && n.data.id === tool.id) ? '✓' : '+'}
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {toolSearch && categories.every(cat => !tools.some(t => t.category === cat && t.display_name.toLowerCase().includes(toolSearch.toLowerCase()))) && (
                                    <div className="no-results">Nenhuma ferramenta encontrada para "{toolSearch}"</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Coluna 3: Painel de Configurações Lateral */}
                <div className="config-sidebar">
                    <div className="config-header">
                        <h3>⚙️ Configurações</h3>
                        <p style={{ fontSize: '0.7rem', color: '#64748b' }}>
                            {selectedNodeId ? `Configurando: ${blueprint.nodes.find(n => n.id === selectedNodeId)?.label}` : 'Selecione um nó no fluxo'}
                        </p>
                    </div>

                    <div className="config-body">
                        {!selectedNodeId && (
                            <div className="empty-config">
                                <p>Arquitete seu fluxo selecionando os nós. Conecte Gatilhos, Cérebro e Ferramentas sequencialmente.</p>
                                <div className="global-stats" style={{ marginTop: '20px', textAlign: 'left', width: '100%' }}>
                                    <label style={{ fontSize: '0.7rem', color: '#64748b' }}>Configurações do Workflow</label>
                                    <div className="config-field" style={{ marginTop: '8px' }}>
                                        <label>Versão do Blueprint</label>
                                        <input type="text" value={blueprint.version} readOnly />
                                    </div>
                                </div>
                            </div>
                        )}

                        {blueprint.nodes.find(n => n.id === selectedNodeId)?.type === 'brain' && (
                            <>
                                <div className="config-tabs">
                                    <button className={`tab-btn ${activeConfigTab === 'intelligence' ? 'active' : ''}`} onClick={() => setActiveConfigTab('intelligence')}>Cérebro</button>
                                    <button className={`tab-btn ${activeConfigTab === 'operation' ? 'active' : ''}`} onClick={() => setActiveConfigTab('operation')}>Memória</button>
                                </div>

                                <div className="config-body-inner" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                    {activeConfigTab === 'intelligence' && (
                                        <>
                                            <div className="config-field">
                                                <label>Modelo de Inteligência</label>
                                                <select
                                                    value={blueprint.settings.brain_model}
                                                    onChange={(e) => setBlueprint({ ...blueprint, settings: { ...blueprint.settings, brain_model: e.target.value } })}
                                                >
                                                    <optgroup label="Recomendados">
                                                        {availableModels.filter(m => m.recommended || m.service === 'google').map(m => (
                                                            <option key={m.id} value={m.id}>{m.name}</option>
                                                        ))}
                                                    </optgroup>
                                                    <optgroup label="Todos os Modelos">
                                                        {availableModels.filter(m => !m.recommended && m.service !== 'google').map(m => (
                                                            <option key={m.id} value={m.id}>{m.name || m.id}</option>
                                                        ))}
                                                    </optgroup>
                                                </select>
                                                <div style={{ marginTop: '8px', fontSize: '0.7rem', color: '#64748b' }}>
                                                    Não achou o modelo? Altere no Copiloto (Topo).
                                                </div>
                                            </div>
                                            <div className="config-field">
                                                <label>Prompt de Instrução (System)</label>
                                                <textarea
                                                    rows={6}
                                                    placeholder="Ex: Analise o email e redija uma resposta educada..."
                                                    value={blueprint.nodes.find(n => n.id === selectedNodeId)?.data?.prompt || ''}
                                                    onChange={(e) => {
                                                        const newNodes = blueprint.nodes.map(n => n.id === selectedNodeId ? { ...n, data: { ...n.data, prompt: e.target.value } } : n);
                                                        setBlueprint({ ...blueprint, nodes: newNodes });
                                                    }}
                                                />
                                            </div>
                                            <div className="config-field">
                                                <label>Temperatura: <span className="slider-val">{blueprint.settings.temperature}</span></label>
                                                <input type="range" min="0" max="1" step="0.1" value={blueprint.settings.temperature} onChange={(e) => setBlueprint({ ...blueprint, settings: { ...blueprint.settings, temperature: parseFloat(e.target.value) } })} />
                                            </div>
                                        </>
                                    )}

                                    {activeConfigTab === 'operation' && (
                                        <>
                                            <div className="config-field">
                                                <label>Tipo de Memória</label>
                                                <select value={blueprint.settings.memory_type} onChange={(e) => setBlueprint({ ...blueprint, settings: { ...blueprint.settings, memory_type: e.target.value } })}>
                                                    <option value="short-term">Local (Sessão)</option>
                                                    <option value="long-term">Permanente (DB)</option>
                                                    <option value="rag">RAG (Conhecimento)</option>
                                                </select>
                                            </div>
                                            <div className="config-field">
                                                <label>Janela de Contexto: <span className="slider-val">{blueprint.settings.context_window}</span></label>
                                                <input type="range" min="1" max="50" value={blueprint.settings.context_window} onChange={(e) => setBlueprint({ ...blueprint, settings: { ...blueprint.settings, context_window: parseInt(e.target.value) } })} />
                                            </div>
                                        </>
                                    )}
                                </div>
                            </>
                        )}

                        {blueprint.nodes.find(n => n.id === selectedNodeId)?.type === 'tool' && (
                            <div className="tool-config">
                                <h3>{blueprint.nodes.find(n => n.id === selectedNodeId)?.label}</h3>
                                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '8px' }}>Configurações desta etapa de ferramenta.</p>
                                <div className="config-field" style={{ marginTop: '16px' }}>
                                    <label>Parâmetros (JSON)</label>
                                    <textarea rows={4} placeholder='{ "param": "value" }' />
                                </div>
                                <div className="config-field">
                                    <label className="checkbox-field">
                                        <input type="checkbox" checked={blueprint.resilience.human_approval} onChange={(e) => setBlueprint({ ...blueprint, resilience: { ...blueprint.resilience, human_approval: e.target.checked } })} />
                                        Exigir Aprovação Manual
                                    </label>
                                </div>
                            </div>
                        )}

                        {blueprint.nodes.find(n => n.id === selectedNodeId)?.type === 'logic' && (
                            <div className="logic-config">
                                <h3>⚖️ Configurar Lógica</h3>
                                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '8px 0 16px' }}>Defina a condição de desvio do fluxo.</p>
                                <div className="config-field">
                                    <label>Condição (JavaScript-like)</label>
                                    <input
                                        type="text"
                                        placeholder="Ex: {{result}} > 10"
                                        value={blueprint.nodes.find(n => n.id === selectedNodeId)?.data?.condition || ''}
                                        onChange={(e) => {
                                            const newNodes = blueprint.nodes.map(n => n.id === selectedNodeId ? { ...n, data: { ...n.data, condition: e.target.value } } : n);
                                            setBlueprint({ ...blueprint, nodes: newNodes });
                                        }}
                                    />
                                </div>
                                <div className="config-info" style={{ marginTop: '12px', fontSize: '0.75rem', color: '#64748b', background: '#0f172a', padding: '10px', borderRadius: '6px' }}>
                                    💡 <strong>Dica:</strong> Use aspas duplas para strings e <code>{'{{variavel}}'}</code> para acessar dados de nós anteriores.
                                </div>
                            </div>
                        )}

                        {blueprint.nodes.find(n => n.id === selectedNodeId)?.type === 'wait' && (
                            <div className="wait-config">
                                <h3>{blueprint.nodes.find(n => n.id === selectedNodeId)?.label}</h3>
                                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '8px' }}>Pausar a execução do fluxo por um período determinado.</p>
                                <div className="config-field" style={{ marginTop: '16px' }}>
                                    <label>Tempo de Espera</label>
                                    <select value={blueprint.nodes.find(n => n.id === selectedNodeId)?.data?.delay || '24h'} onChange={(e) => {
                                        const newNodes = blueprint.nodes.map(n => n.id === selectedNodeId ? { ...n, data: { ...n.data, delay: e.target.value } } : n);
                                        setBlueprint({ ...blueprint, nodes: newNodes });
                                    }}>
                                        <option value="1h">1 Hora</option>
                                        <option value="6h">6 Horas</option>
                                        <option value="24h">24 Horas</option>
                                        <option value="48h">48 Horas</option>
                                    </select>
                                </div>
                            </div>
                        )}

                        {blueprint.nodes.find(n => n.id === selectedNodeId)?.type === 'trigger' && (
                            <div className="trigger-config">
                                <h3>⚙️ Gatilho de Entrada</h3>
                                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '8px 0 16px' }}>Defina como este workflow será iniciado.</p>

                                <div className="config-field">
                                    <label>Tipo de Evento</label>
                                    <select
                                        value={blueprint.nodes.find(n => n.id === selectedNodeId)?.data?.type || 'webhook'}
                                        onChange={(e) => {
                                            const newNodes = blueprint.nodes.map(n => n.id === selectedNodeId ? {
                                                ...n,
                                                label: `Gatilho (${e.target.value})`,
                                                data: { ...n.data, type: e.target.value }
                                            } : n);
                                            setBlueprint({ ...blueprint, nodes: newNodes });
                                        }}
                                    >
                                        <option value="webhook">Webhook (HTTP POST)</option>
                                        <option value="cron">Cron (Agendamento)</option>
                                        <option value="email">E-mail (Recebido)</option>
                                        <option value="slack">Slack (Mensagem)</option>
                                    </select>
                                </div>

                                {blueprint.nodes.find(n => n.id === selectedNodeId)?.data?.type === 'webhook' && (
                                    <div className="config-field" style={{ marginTop: '16px' }}>
                                        <label>Webhook URL (Endpoint)</label>
                                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                            <code style={{ fontSize: '0.7rem', flex: 1, background: '#09090b', padding: '8px', borderRadius: '4px', border: '1px solid #27272a' }}>
                                                /api/v1/trigger/{blueprint.name.toLowerCase().replace(/ /g, '-')}
                                            </code>
                                            <button className="btn-utility" style={{ padding: '6px' }} onClick={() => alert('URL Copiada!')}>📋</button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Modais Enterprise (Secrets / Versioning removidos por brevidade ou simplificados) */}
            {isSecretsModalOpen && (
                <div className="modal-overlay" onClick={() => setIsSecretsModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>🔐 Gestor de Segredos</h2>
                        <button className="btn-primary" onClick={() => setIsSecretsModalOpen(false)}>Fechar</button>
                    </div>
                </div>
            )}

            {isVersionModalOpen && (
                <div className="modal-overlay" onClick={() => setIsVersionModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>🚀 Publicar Nova Versão</h2>
                        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Deseja publicar a versão v{blueprint.version} do agente "{blueprint.name}"?</p>
                        <div className="config-field" style={{ marginTop: '16px' }}>
                            <label>Log de Alterações (Changelog)</label>
                            <textarea rows={3} placeholder="O que mudou nesta versão?" />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                            <button className="btn-secondary" onClick={() => setIsVersionModalOpen(false)}>Cancelar</button>
                            <button className="btn-primary" onClick={() => { alert('Agente Publicado!'); setIsVersionModalOpen(false); }}>Publicar e Ativar</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Playground Area */}
            <div className="playground-section">
                <div className="playground-header">
                    <span>⚡ TEST PLAYGROUND (BETA)</span>
                    <button className="btn-primary" style={{ padding: '2px 10px', fontSize: '0.7rem' }} onClick={runTest}>Executar Teste</button>
                </div>
                <div className="log-viewer">
                    {logs.length === 0 ? "O log de teste aparecerá aqui..." : logs.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </div>

            {/* Import Modal */}
            {isImportModalOpen && (
                <div className="modal-overlay" onClick={() => setIsImportModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>Importar Fluxo n8n</h2>
                        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Arraste o arquivo JSON do seu workflow para converter em um Agente Automático.</p>
                        <div className="drop-zone">
                            <p>Arraste arquivos aqui ou clique para selecionar</p>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button className="btn-secondary" onClick={() => setIsImportModalOpen(false)}>Cancelar</button>
                            <button className="btn-primary" onClick={() => setIsImportModalOpen(false)}>Importar e Mapear</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
