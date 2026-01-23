import React, { useState } from 'react';
import { CatalogStatusResponse, ApiKeyStatus } from '../../services/api';
import './ApiKeyManager.css';

// Reusing interface (ideally move to types.ts)
interface ApiKey {
    id: string;
    service: string;
    key: string;
    isActive: boolean;
    status?: ApiKeyStatus | null;
    checkingStatus?: boolean;
}

interface ModelsTabProps {
    apiKeys: ApiKey[];
    catalogStatus: CatalogStatusResponse | null;
    userPrefs: any;
    onSyncCatalog: () => Promise<void>;
}

export const ModelsTab: React.FC<ModelsTabProps> = ({
    apiKeys,
    catalogStatus,
    userPrefs,
    onSyncCatalog
}) => {
    const [selectedActivity, setSelectedActivity] = useState<string>('all');
    const [filterByPrefs, setFilterByPrefs] = useState<boolean>(false);

    const categoryLabels: { [key: string]: string } = {
        'text': '📝 Escrita (Geral)',
        'reasoning': '🧠 Raciocínio (o1/R1)',
        'audio': '🎵 Áudio',
        'image': '🖼️ Imagem (Geração)',
        'video': '🎬 Vídeo',
        'code': '💻 Código',
        'multimodal': '🌐 Multimodal (Vision)',
        'long_context': '📚 Longo Contexto (1M+)',
        'chat': '💬 Chat/Instrução',
        'translation': '🔤 Tradução',
        'creative': '✍️ Criativo',
        'structured': '📊 Dados Estruturados',
        'small_model': '⚡ Baixa Latência'
    };

    const categoryOrder = [
        'multimodal', 'reasoning', 'code', 'long_context',
        'chat', 'text', 'image', 'video', 'audio',
        'translation', 'creative', 'structured', 'small_model'
    ];

    const getFilteredModels = () => {
        // Coleta todos os modelos de todas as chaves ativas
        let allModels: any[] = [];
        apiKeys.forEach(key => {
            if (key.status && key.status.models_status) {
                allModels = [...allModels, ...key.status.models_status];
            }
        });

        // Remove duplicatas (opcional, mas bom pra UI limpa se tiver keys repetidas de serviços diferentes que dão acesso aos mesmos modelos, embora raro aqui)
        // Por enquanto vamos assumir que queremos ver por chave mesmo, mas a UI original agrupava por chave.
        // O requisito diz "Visualizar os recursos disponíveis sem poluir".
        // A UI original renderizava dentro do card da chave. Aqui estamos separando.
        // Vamos agrupar puramente por categoria, independente da chave de origem.

        // 1. Filtro por Atividade (selectedActivity)
        let filteredModels = allModels;
        if (selectedActivity !== 'all') {
            filteredModels = filteredModels.filter(m => m.category === selectedActivity || (selectedActivity === 'text' && !m.category));
        }

        // 2. Filtro por Preferências (filterByPrefs)
        if (filterByPrefs && userPrefs) {
            const mode = userPrefs.usage_mode || 'free';
            if (mode === 'free') {
                filteredModels = filteredModels.filter(m => m.tier === 'free');
            } else {
                const strategyKey = `${selectedActivity === 'all' ? 'global' : selectedActivity}_strategy`;
                const strategy = userPrefs[strategyKey] || userPrefs.global_strategy || 'performance';
                if (strategy === 'free') {
                    filteredModels = filteredModels.filter(m => m.tier === 'free');
                }
            }
        }

        return filteredModels;
    };

    // Calcula categorias e contagem de modelos para os filtros
    const getCategoryCounts = () => {
        let allModels: any[] = [];
        apiKeys.forEach(key => {
            if (key.status && key.status.models_status) {
                allModels = [...allModels, ...key.status.models_status];
            }
        });

        const counts: { [key: string]: number } = { all: allModels.length };
        allModels.forEach(m => {
            const cat = m.category || 'text';
            counts[cat] = (counts[cat] || 0) + 1;
        });

        return counts;
    };

    const categoryCounts = getCategoryCounts();
    const availableCategories = categoryOrder.filter(c => (categoryCounts[c] || 0) > 0);

    const renderModelList = () => {
        const filteredModels = getFilteredModels();

        // Agrupa por categoria
        const grouped: { [key: string]: any[] } = {};
        filteredModels.forEach(model => {
            const cat = model.category || 'text';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(model);
        });

        return categoryOrder.map(category => {
            const models = grouped[category];
            if (!models || models.length === 0) return null;

            return (
                <div key={category} className="model-category-group" style={{ marginBottom: '24px' }}>
                    <div className="model-category-header" style={{
                        borderBottom: '2px solid var(--border-color)',
                        paddingBottom: '8px',
                        marginBottom: '12px',
                        fontSize: '1.2rem'
                    }}>
                        {categoryLabels[category] || category}
                    </div>
                    <div className="models-grid" style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                        gap: '12px'
                    }}>
                        {models.map((model, idx) => (
                            <div key={`${model.name}-${idx}`} className={`model-item ${model.status}`} style={{
                                padding: '12px',
                                borderRadius: '8px',
                                backgroundColor: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '8px'
                            }}>
                                <div style={{ fontWeight: 'bold', wordBreak: 'break-all' }}>{model.name}</div>
                                <div className="model-badge" style={{ fontSize: '0.85rem' }}>
                                    {model.available && !model.blocked ? '✅ Disponível' :
                                        model.blocked ? '❌ Bloqueado' : '⚠️ Desconhecido'}
                                </div>
                                {model.tier === 'free' && (
                                    <div className="model-tier-info" style={{ fontSize: '0.8rem', opacity: 0.9, color: '#10b981', fontWeight: 'bold' }}>
                                        🆓 Grátis
                                    </div>
                                )}
                                {model.tier === 'paid' && (
                                    <div className="model-tier-info" style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                                        <div style={{ color: '#fbbf24', fontWeight: 'bold' }}>💰 Pago</div>
                                        <div style={{ fontSize: '0.75rem', marginTop: '2px' }}>
                                            In: ${((model.input_price || 0) * 1000000).toFixed(2)} / 1M tokens
                                        </div>
                                        <div style={{ fontSize: '0.75rem' }}>
                                            Out: ${((model.output_price || 0) * 1000000).toFixed(2)} / 1M tokens
                                        </div>
                                    </div>
                                )}
                                {model.tier === 'unknown' && <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>❓ Tier desconhecido</div>}
                                <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: 'auto' }}>
                                    Via: {apiKeys.length > 0 ? "Provedores Ativos" : "Nenhum provedor"}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        });
    };

    const hasActiveKeys = apiKeys.some(k => k.status && k.status.is_valid);

    return (
        <div className="models-tab">
            {/* Filtros de Visualização */}
            <div className="api-dashboard-filters" style={{
                padding: '20px',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '12px',
                marginBottom: '20px',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '20px',
                alignItems: 'center',
                border: '1px solid var(--border-color)'
            }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                    <label style={{ fontWeight: 'bold', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Filtro por Categoria:</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                            onClick={() => setSelectedActivity('all')}
                            style={{
                                padding: '6px 14px',
                                borderRadius: '20px',
                                border: '1px solid var(--border-color)',
                                background: selectedActivity === 'all' ? 'var(--primary-color)' : 'var(--bg-card)',
                                color: selectedActivity === 'all' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontSize: '0.85rem'
                            }}
                        >
                            Todos ({categoryCounts.all})
                        </button>
                        {availableCategories.map(activity => (
                            <button
                                key={activity}
                                onClick={() => setSelectedActivity(activity)}
                                style={{
                                    padding: '6px 14px',
                                    borderRadius: '20px',
                                    border: '1px solid var(--border-color)',
                                    background: selectedActivity === activity ? 'var(--primary-color)' : 'var(--bg-card)',
                                    color: selectedActivity === activity ? 'white' : 'var(--text-primary)',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem'
                                }}
                            >
                                {(categoryLabels[activity] || activity).replace(/ \(.*\)/, '')} ({categoryCounts[activity] || 0})
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <input
                        type="checkbox"
                        id="filterByPrefs"
                        checked={filterByPrefs}
                        onChange={(e) => setFilterByPrefs(e.target.checked)}
                        style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <label htmlFor="filterByPrefs" style={{ fontWeight: '600', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        Filtrar por minhas preferências
                    </label>
                </div>
            </div>

            {/* Notificação sobre status do catálogo */}
            {catalogStatus && (!catalogStatus.api_available || catalogStatus.using_mock_data || catalogStatus.api_error) && (
                <div className="catalog-warning" style={{
                    padding: '12px 16px',
                    marginBottom: '20px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-warning, #fff3cd)',
                    border: '1px solid var(--border-warning, #ffc107)',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <span style={{ fontSize: '20px' }}>⚠️</span>
                    <div style={{ flex: 1 }}>
                        <strong>Catálogo de Modelos:</strong>
                        {catalogStatus.using_mock_data && (
                            <div>API do Chatbot Arena não disponível. Usando dados mockados.</div>
                        )}
                        {catalogStatus.api_error && !catalogStatus.using_mock_data && (
                            <div>{catalogStatus.api_error}</div>
                        )}
                        {!catalogStatus.is_populated && (
                            <div>Catálogo ainda não foi populado.</div>
                        )}
                        {catalogStatus.total_models > 0 && (
                            <div style={{ fontSize: '0.9em', marginTop: '4px', opacity: 0.8 }}>
                                {catalogStatus.total_models} modelo(s) cadastrado(s)
                            </div>
                        )}
                    </div>
                    <button
                        onClick={async () => {
                            try {
                                await onSyncCatalog();
                                alert('Catálogo sincronizado com sucesso!');
                            } catch (error: any) {
                                alert('Erro ao sincronizar catálogo: ' + (error.response?.data?.detail || error.message));
                            }
                        }}
                        style={{
                            padding: '6px 12px',
                            borderRadius: '4px',
                            border: '1px solid var(--border-warning, #ffc107)',
                            backgroundColor: 'var(--bg-card)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer'
                        }}
                    >
                        Sincronizar
                    </button>
                </div>
            )}

            {/* Grid de Modelos */}
            {hasActiveKeys ? (
                <div className="models-list-container">
                    {renderModelList()}
                </div>
            ) : (
                <div style={{
                    textAlign: 'center',
                    padding: '40px',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: '12px',
                    border: '1px dashed var(--border-color)'
                }}>
                    <h3>Nenhum modelo disponível</h3>
                    <p>Adicione chaves de API na aba "Chaves API" para ver os modelos disponíveis.</p>
                </div>
            )}
        </div>
    );
};
