import React, { useState } from 'react';
import { ApiKeyStatus } from '../../services/api';
import './ApiKeyManager.css';

// Reusing interfaces from main file (or they should be moved to a types file)
export interface ApiKey {
    id: string;
    service: string;
    key: string;
    isActive: boolean;
    status?: ApiKeyStatus | null;
    checkingStatus?: boolean;
    backendId?: string;
}

interface ProvidersTabProps {
    apiKeys: ApiKey[];
    services: { id: string; name: string; icon: string; url: string }[];
    onSave: (service: string, key: string, apiKeyId?: string) => Promise<void>;
    onDelete: (id: string, service: string, backendId?: string) => Promise<void>;
    onCheckStatus: (apiKey: ApiKey) => Promise<void>;
}

export const ProvidersTab: React.FC<ProvidersTabProps> = ({
    apiKeys,
    services,
    onSave,
    onDelete,
    onCheckStatus
}) => {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [newKey, setNewKey] = useState({ service: 'gemini', key: '' });
    const [editKeyValue, setEditKeyValue] = useState<string>('');

    const handleAdd = () => {
        if (newKey.key.trim()) {
            onSave(newKey.service, newKey.key.trim());
            setNewKey(prev => ({ ...prev, key: '' }));
        }
    };

    const startEditing = (apiKey: ApiKey) => {
        setEditingId(apiKey.id);
        setEditKeyValue(apiKey.key);
    };

    const cancelEditing = () => {
        setEditingId(null);
        setEditKeyValue('');
    };

    const saveEdit = (apiKey: ApiKey) => {
        if (editKeyValue.trim()) {
            onSave(apiKey.service, editKeyValue.trim(), apiKey.backendId);
            setEditingId(null);
        }
    };

    const getServiceInfo = (serviceId: string) => {
        return services.find(s => s.id === serviceId) || services[0];
    };

    return (
        <div className="providers-tab">
            <div className="api-key-list">
                {apiKeys.map((apiKey) => {
                    const serviceInfo = getServiceInfo(apiKey.service);
                    return (
                        <div key={apiKey.id} className="api-key-item" style={{
                            border: apiKey.status?.is_valid ? '2px solid var(--success-color, #28a745)' : '1px solid var(--border-color)',
                            backgroundColor: apiKey.status?.is_valid ? 'var(--bg-success-light, rgba(40, 167, 69, 0.05))' : 'var(--bg-secondary)',
                            transition: 'all 0.3s ease'
                        }}>
                            <div className="api-key-item-header">
                                <div className="api-key-service">
                                    <span className="service-icon" style={{ fontSize: '1.5rem' }}>{serviceInfo.icon}</span>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <h4 style={{ margin: 0 }}>{serviceInfo.name}</h4>
                                            {apiKey.status?.is_valid && (
                                                <span className="status-badge-success" style={{
                                                    fontSize: '0.7rem',
                                                    backgroundColor: 'var(--success-color, #28a745)',
                                                    color: 'white',
                                                    padding: '2px 6px',
                                                    borderRadius: '4px',
                                                    fontWeight: 'bold'
                                                }}>CONECTADO</span>
                                            )}
                                        </div>
                                        <p className="api-key-preview">
                                            {editingId === apiKey.id
                                                ? editKeyValue
                                                : apiKey.key === '••••••••••••••••'
                                                    ? 'Chave salva (oculta)'
                                                    : `${apiKey.key.substring(0, 12)}...${apiKey.key.substring(apiKey.key.length - 4)}`}
                                        </p>
                                    </div>
                                </div>
                                <div className="api-key-actions">
                                    {editingId === apiKey.id ? (
                                        <>
                                            <button
                                                onClick={() => saveEdit(apiKey)}
                                                className="btn-save"
                                            >
                                                Salvar
                                            </button>
                                            <button
                                                onClick={cancelEditing}
                                                className="btn-cancel"
                                            >
                                                Cancelar
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={() => startEditing(apiKey)}
                                                className="btn-edit"
                                            >
                                                Editar
                                            </button>
                                            <button
                                                onClick={() => onDelete(apiKey.id, apiKey.service, apiKey.backendId)}
                                                className="btn-delete"
                                            >
                                                Remover
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {editingId === apiKey.id && (
                                <input
                                    type="password"
                                    value={editKeyValue}
                                    onChange={(e) => setEditKeyValue(e.target.value)}
                                    className="api-key-edit-input"
                                    placeholder="Cole a chave de API"
                                    style={{ marginTop: '10px' }}
                                />
                            )}

                            {/* Status e Cotas Simplificado */}
                            {!editingId && (
                                <div className="api-key-status" style={{ marginTop: '12px' }}>
                                    {/* Botão de verificar apenas se não estiver válido ou se quiser forçar revalidação */}
                                    {!apiKey.status?.is_valid && (
                                        <button
                                            onClick={() => onCheckStatus(apiKey)}
                                            disabled={apiKey.checkingStatus}
                                            className="btn-check-status"
                                            style={{ width: '100%', marginBottom: '10px' }}
                                        >
                                            {apiKey.checkingStatus ? '🔄 Conectando...' : '🔌 Conectar / Verificar'}
                                        </button>
                                    )}

                                    {apiKey.status && (
                                        <div className="quota-info">
                                            {!apiKey.status.is_valid && (
                                                <div className="quota-status invalid" style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'rgba(220, 53, 69, 0.1)', border: '1px solid rgba(220, 53, 69, 0.3)' }}>
                                                    <span className="status-indicator">❌</span>
                                                    <span className="status-text">Falha na conexão</span>
                                                </div>
                                            )}

                                            {/* Exibir apenas informações críticas de saldo/créditos nesta aba */}
                                            {apiKey.status.is_valid && (
                                                <div style={{ marginTop: '5px' }}>
                                                    {apiKey.status.credits !== undefined && apiKey.status.credits !== null && (
                                                        <div className="credits-dashboard" style={{
                                                            padding: '8px 12px',
                                                            background: 'rgba(255, 255, 255, 0.5)',
                                                            borderRadius: '6px',
                                                            border: '1px solid var(--success-color, #28a745)',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'space-between',
                                                            fontSize: '0.9rem'
                                                        }}>
                                                            <span style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>💰 Saldo:</span>
                                                            <span style={{
                                                                fontWeight: 'bold',
                                                                color: apiKey.status.credits?.toString().startsWith('-') ? '#dc3545' : 'var(--success-color, #28a745)',
                                                                fontFamily: 'monospace',
                                                                fontSize: '1.1rem'
                                                            }}>
                                                                {apiKey.status.credits}
                                                            </span>
                                                        </div>
                                                    )}
                                                    <div style={{ textAlign: 'right', marginTop: '4px', fontSize: '0.75rem', color: 'var(--text-secondary)', opacity: 0.8 }}>
                                                        <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => onCheckStatus(apiKey)}>
                                                            {apiKey.checkingStatus ? 'Atualizando...' : 'Atualizar saldo'}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}

                                            {apiKey.status.error && (
                                                <div className="quota-error" style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--error-color, #dc3545)' }}>
                                                    ⚠️ {apiKey.status.error}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="api-key-add">
                <h3>Adicionar Nova Chave</h3>
                <div className="api-key-add-form">
                    <select
                        value={newKey.service}
                        onChange={(e) => setNewKey({ ...newKey, service: e.target.value })}
                        className="api-key-service-select"
                    >
                        {services.map((service) => (
                            <option key={service.id} value={service.id}>
                                {service.icon} {service.name}
                            </option>
                        ))}
                    </select>
                    <input
                        type="password"
                        value={newKey.key}
                        onChange={(e) => setNewKey({ ...newKey, key: e.target.value })}
                        placeholder="Cole sua chave de API aqui"
                        className="api-key-add-input"
                    />
                    <div className="api-key-add-actions">
                        <a
                            href={getServiceInfo(newKey.service).url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="api-key-link-btn"
                        >
                            Obter Chave
                        </a>
                        <button
                            onClick={handleAdd}
                            disabled={!newKey.key.trim()}
                            className="btn-add"
                        >
                            Adicionar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
