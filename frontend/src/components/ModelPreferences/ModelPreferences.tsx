import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/api';

const STRATEGIES = [
    { value: 'performance', label: 'Alto Desempenho (Melhores Modelos)' },
    { value: 'cost_benefit', label: 'Custo-Benefício (Equilíbrio)' },
    { value: 'speed', label: 'Velocidade (Respostas Rápidas)' },
    { value: 'cheapest', label: 'Mais Barato (Economia)' },
    { value: 'free', label: 'Gratuito (Somente Free Tier)' }
];

export const ModelPreferences = () => {
    const { isAuthenticated } = useAuth();
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [preferences, setPreferences] = useState({
        usage_mode: 'free',
        global_strategy: 'performance',
        chat_strategy: 'global',
        code_strategy: 'global',
        vision_strategy: 'global',
        video_strategy: 'global',
        multimodal_strategy: 'global',
        translation_strategy: 'global',
        reasoning_strategy: 'global',
        long_context_strategy: 'global',
        audio_strategy: 'global',
        creative_strategy: 'global',
        structured_strategy: 'global',
        small_model_strategy: 'global'
    });
    const [message, setMessage] = useState({ text: '', type: '' });

    useEffect(() => {
        if (isAuthenticated) {
            loadPreferences();
        }
    }, [isAuthenticated]);

    const loadPreferences = async () => {
        setLoading(true);
        try {
            const response = await api.get('/api/auth/me');
            const prefs = response.data.model_preferences || {};

            setPreferences({
                usage_mode: prefs.usage_mode || 'free',
                global_strategy: prefs.global_strategy || 'performance',
                chat_strategy: prefs.chat_strategy || 'global',
                code_strategy: prefs.code_strategy || 'global',
                vision_strategy: prefs.vision_strategy || 'global',
                video_strategy: prefs.video_strategy || 'global',
                multimodal_strategy: prefs.multimodal_strategy || 'global',
                translation_strategy: prefs.translation_strategy || 'global',
                reasoning_strategy: prefs.reasoning_strategy || 'global',
                long_context_strategy: prefs.long_context_strategy || 'global',
                audio_strategy: prefs.audio_strategy || 'global',
                creative_strategy: prefs.creative_strategy || 'global',
                structured_strategy: prefs.structured_strategy || 'global',
                small_model_strategy: prefs.small_model_strategy || 'global'
            });
        } catch (error) {
            console.error('Erro ao carregar preferências:', error);
            setMessage({ type: 'error', text: 'Erro ao carregar preferências.' });
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage({ text: '', type: '' });
        try {
            await api.put('/api/user/preferences/', preferences);
            setMessage({ type: 'success', text: 'Preferências salvas com sucesso!' });
        } catch (error) {
            console.error('Erro ao salvar:', error);
            setMessage({ type: 'error', text: 'Erro ao salvar preferências.' });
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div style={{ padding: '20px', color: 'var(--text-secondary)' }}>Carregando preferências...</div>;

    const CategorySelector = ({ label, value, onChange, disabled, icon }: any) => (
        <div className="preference-item" style={{
            padding: '12px',
            background: 'var(--bg-card)',
            borderRadius: '10px',
            border: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            opacity: disabled ? 0.5 : 1,
            transition: 'all 0.2s'
        }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
                <span>{icon}</span> {label}
            </label>
            <select
                value={value}
                onChange={onChange}
                disabled={disabled}
                style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    fontSize: '0.9rem',
                    outline: 'none'
                }}
            >
                <option value="global">Seguir Global</option>
                {STRATEGIES.map(s => (
                    <option key={s.value} value={s.value}>{s.label.split(' (')[0]}</option>
                ))}
            </select>
        </div>
    );

    return (
        <div className="model-preferences-container" style={{ padding: '20px', maxWidth: '1000px' }}>
            <h3 style={{ marginBottom: '10px', color: 'var(--text-primary)' }}>Inteligência do sistema</h3>
            <p style={{ marginBottom: '30px', color: 'var(--text-secondary)' }}>
                Configure como o sistema deve escolher automaticamente os modelos de IA para cada tipo de tarefa.
            </p>

            <div style={{ display: 'grid', gap: '24px' }}>

                {/* 1. Master Toggle: Modo de Uso */}
                <div className="preference-group master-toggle" style={{
                    padding: '24px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '16px',
                    background: 'var(--bg-secondary)',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                                Modo de Uso
                            </label>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                {preferences.usage_mode === 'free'
                                    ? 'Focado em economia e uso gratuito prioritário'
                                    : 'Acesso total e configurações avançadas de agentes'}
                            </span>
                        </div>
                        <div style={{
                            display: 'flex',
                            background: 'var(--bg-card)',
                            borderRadius: '12px',
                            padding: '4px',
                            border: '1px solid var(--border-color)',
                            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)'
                        }}>
                            <button
                                onClick={() => setPreferences({ ...preferences, usage_mode: 'free' })}
                                style={{
                                    padding: '10px 24px',
                                    borderRadius: '10px',
                                    border: 'none',
                                    cursor: 'pointer',
                                    background: preferences.usage_mode === 'free' ? 'linear-gradient(135deg, var(--primary-color), #9333ea)' : 'transparent',
                                    color: preferences.usage_mode === 'free' ? 'white' : 'var(--text-secondary)',
                                    fontWeight: 'bold',
                                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                    boxShadow: preferences.usage_mode === 'free' ? '0 4px 15px rgba(124, 58, 237, 0.4)' : 'none',
                                    transform: preferences.usage_mode === 'free' ? 'scale(1.05)' : 'scale(1)',
                                    zIndex: preferences.usage_mode === 'free' ? 2 : 1
                                }}
                            >
                                Total Grátis
                            </button>
                            <button
                                onClick={() => setPreferences({ ...preferences, usage_mode: 'paid' })}
                                style={{
                                    padding: '10px 24px',
                                    borderRadius: '10px',
                                    border: 'none',
                                    cursor: 'pointer',
                                    background: preferences.usage_mode === 'paid' ? 'linear-gradient(135deg, var(--primary-color), #9333ea)' : 'transparent',
                                    color: preferences.usage_mode === 'paid' ? 'white' : 'var(--text-secondary)',
                                    fontWeight: 'bold',
                                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                    boxShadow: preferences.usage_mode === 'paid' ? '0 4px 15px rgba(124, 58, 237, 0.4)' : 'none',
                                    transform: preferences.usage_mode === 'paid' ? 'scale(1.05)' : 'scale(1)',
                                    zIndex: preferences.usage_mode === 'paid' ? 2 : 1
                                }}
                            >
                                Personalizado
                            </button>
                        </div>
                    </div>
                </div>

                {/* 2. Estratégia Global (Base) */}
                <div className="preference-group" style={{
                    padding: '20px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '12px',
                    background: 'var(--bg-secondary)',
                    opacity: preferences.usage_mode === 'free' ? 0.6 : 1
                }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '12px', color: 'var(--text-primary)' }}>
                        Estratégia Global (Master)
                    </label>
                    <select
                        value={preferences.global_strategy}
                        onChange={(e) => setPreferences({ ...preferences, global_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                        style={{
                            width: '100%',
                            padding: '12px',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-card)',
                            color: 'var(--text-primary)',
                            cursor: preferences.usage_mode === 'free' ? 'not-allowed' : 'pointer'
                        }}
                    >
                        {STRATEGIES.map(s => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                    </select>
                </div>

                {/* 3. Estratégias por Agente */}
                <div className="preference-group" style={{
                    padding: '24px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '16px',
                    background: 'var(--bg-secondary)',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
                    gap: '16px'
                }}>
                    <h4 style={{ gridColumn: '1/-1', margin: '0 0 10px 0', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🤖 Agentes Especializados
                    </h4>

                    <CategorySelector
                        icon="💬" label="Chat (Texto)"
                        value={preferences.chat_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, chat_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="💻" label="Código"
                        value={preferences.code_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, code_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🖼️" label="Visão"
                        value={preferences.vision_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, vision_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🎬" label="Vídeo"
                        value={preferences.video_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, video_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🌐" label="Multimodal"
                        value={preferences.multimodal_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, multimodal_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🔤" label="Tradução"
                        value={preferences.translation_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, translation_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🧠" label="Raciocínio Lógico"
                        value={preferences.reasoning_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, reasoning_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="📚" label="Longo Contexto"
                        value={preferences.long_context_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, long_context_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="🎤" label="Áudio Nativo"
                        value={preferences.audio_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, audio_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="✍️" label="Escrita Criativa"
                        value={preferences.creative_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, creative_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="📊" label="Dados Estruturados"
                        value={preferences.structured_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, structured_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                    <CategorySelector
                        icon="⚡" label="Baixa Latência"
                        value={preferences.small_model_strategy}
                        onChange={(e: any) => setPreferences({ ...preferences, small_model_strategy: e.target.value })}
                        disabled={preferences.usage_mode === 'free'}
                    />
                </div>

            </div>

            <div style={{ marginTop: '30px' }}>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        padding: '12px 32px',
                        backgroundColor: '#7c3aed',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        opacity: saving ? 0.7 : 1,
                        fontWeight: '600',
                        fontSize: '1rem',
                        transition: 'all 0.2s',
                        boxShadow: '0 4px 6px rgba(124, 58, 237, 0.2)'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#6d28d9'}
                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#7c3aed'}
                >
                    {saving ? 'Salvando...' : 'Salvar Preferências'}
                </button>
            </div>

            {message.text && (
                <div style={{
                    marginTop: '24px',
                    padding: '16px',
                    borderRadius: '8px',
                    backgroundColor: message.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                    color: message.type === 'error' ? '#ef4444' : '#10b981',
                    border: `1px solid ${message.type === 'error' ? '#ef4444' : '#10b981'}`,
                    fontWeight: '500'
                }}>
                    {message.type === 'error' ? '❌' : '✅'} {message.text}
                </div>
            )}
        </div>
    );
};

