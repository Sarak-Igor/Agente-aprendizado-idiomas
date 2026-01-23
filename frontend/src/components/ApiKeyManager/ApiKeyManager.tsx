import { useState, useEffect } from 'react';
import { apiKeysApi, ApiKeyStatus, ApiKeyResponse, modelCatalogApi, CatalogStatusResponse } from '../../services/api';
import api from '../../services/api';
import './ApiKeyManager.css';
import { ProvidersTab, ApiKey } from './ProvidersTab';
import { ModelsTab } from './ModelsTab';

const SERVICES = [
  { id: 'gemini', name: 'Google Gemini', icon: '🤖', url: 'https://aistudio.google.com/apikey' },
  { id: 'openrouter', name: 'OpenRouter', icon: '🌐', url: 'https://openrouter.ai/keys' },
  { id: 'groq', name: 'Groq', icon: '⚡', url: 'https://console.groq.com/keys' },
  { id: 'together', name: 'Together AI', icon: '🤝', url: 'https://api.together.xyz/settings/api-keys' },
];

export const ApiKeyManager = () => {
  const [activeTab, setActiveTab] = useState<'providers' | 'models'>('providers');
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatusResponse | null>(null);
  const [userPrefs, setUserPrefs] = useState<any>(null);

  useEffect(() => {
    loadApiKeys();
    checkCatalogStatus();
    loadUserPreferences();
  }, []);

  const loadUserPreferences = async () => {
    try {
      const response = await api.get('/api/auth/me');
      setUserPrefs(response.data.model_preferences || {});
    } catch (error) {
      console.error('Erro ao carregar preferências:', error);
    }
  };

  const checkCatalogStatus = async () => {
    try {
      const status = await modelCatalogApi.getStatus();
      setCatalogStatus(status);
    } catch (error) {
      console.error('Erro ao verificar status do catálogo:', error);
    }
  };

  const loadApiKeys = async () => {
    try {
      // Carrega chaves do backend (do usuário atual)
      const response = await apiKeysApi.list();
      const backendKeys = response.api_keys || [];

      // Converte para formato local (sem expor as chaves - backend não retorna)
      // Por enquanto, vamos mostrar apenas os serviços que têm chaves salvas
      const keys: ApiKey[] = backendKeys.map((bk: ApiKeyResponse) => ({
        id: `${bk.service}-${bk.id}`,
        backendId: bk.id,
        service: bk.service,
        key: '••••••••••••••••', // Não expõe a chave real
        isActive: bk.service === 'gemini',
        status: null,
        checkingStatus: false,
      }));

      setApiKeys(keys);

      // Verificação automática de status para todas as chaves carregadas
      if (keys.length > 0) {
        // Pequeno delay para garantir que o estado inicial foi renderizado
        setTimeout(() => {
          keys.forEach(key => {
            checkApiKeyStatus(key);
          });
        }, 100);
      }
    } catch (error) {
      console.error('Erro ao carregar chaves de API:', error);
      setApiKeys([]);
    }
  };

  const handleSave = async (service: string, key: string, apiKeyId?: string) => {
    try {
      const trimmedKey = key.trim();

      if (!trimmedKey) {
        return;
      }

      // Salva no backend
      if (apiKeyId) {
        // TODO: Implement update if needed, currently API might only support create/delete or we treat save as create
        // For simplicity and existing logic parity:
        await apiKeysApi.create({
          service,
          api_key: trimmedKey,
        });
      } else {
        await apiKeysApi.create({
          service,
          api_key: trimmedKey,
        });
      }

      // Atualiza a lista de chaves
      await loadApiKeys();

      // Verifica status automaticamente após salvar
      if (['gemini', 'openrouter', 'groq', 'together'].includes(service)) {
        // Busca a chave recém-salva para verificar status
        setTimeout(async () => {
          const updatedKeys = await apiKeysApi.list();
          const savedKey = updatedKeys.api_keys.find((k: ApiKeyResponse) => k.service === service);
          if (savedKey) {
            // Para verificar status, precisamos da chave real (que acabamos de salvar)
            checkApiKeyStatus({
              id: `${service}-${savedKey.id}`,
              backendId: savedKey.id,
              service: service,
              key: trimmedKey, // Usa a chave que acabamos de salvar
              isActive: service === 'gemini',
              status: null,
              checkingStatus: false,
            });
          }
        }, 500);
      }
    } catch (error: any) {
      console.error('Erro ao salvar chave de API:', error);
      alert(error.response?.data?.detail || 'Erro ao salvar chave de API');
    }
  };

  const handleDelete = async (_id: string, service: string, backendId?: string) => {
    try {
      if (backendId) {
        await apiKeysApi.delete(backendId);
      } else {
        // Fallback: tenta deletar por serviço
        await apiKeysApi.deleteByService(service);
      }
      await loadApiKeys();
    } catch (error: any) {
      console.error('Erro ao deletar chave de API:', error);
      alert(error.response?.data?.detail || 'Erro ao deletar chave de API');
    }
  };

  const checkApiKeyStatus = async (apiKey: ApiKey) => {
    // Marca como verificando usando função de callback para garantir estado atualizado
    setApiKeys(prevKeys => prevKeys.map(k =>
      k.id === apiKey.id || (k.service === apiKey.service && k.key === apiKey.key)
        ? { ...k, checkingStatus: true }
        : k
    ));

    try {
      let status: ApiKeyStatus;

      // Se a chave está salva no backend (não visível), usa rota especial
      if (apiKey.key === '••••••••••••••••' && apiKey.backendId) {
        status = await apiKeysApi.checkSavedStatus(apiKey.service);
      } else {
        // Se a chave está sendo editada/fornecida, usa rota normal
        status = await apiKeysApi.checkStatus(apiKey.key, apiKey.service);
      }

      // Atualiza status usando função de callback
      setApiKeys(prevKeys => prevKeys.map(k =>
        k.id === apiKey.id || (k.service === apiKey.service && k.key === apiKey.key)
          ? { ...k, status, checkingStatus: false }
          : k
      ));
    } catch (error: any) {
      console.error('Erro ao verificar status:', error);
      const errorStatus: ApiKeyStatus = {
        service: apiKey.service,
        is_valid: false,
        models_status: [],
        available_models: [],
        blocked_models: [],
        error: error.response?.data?.detail || 'Erro ao verificar status da chave'
      };

      // Atualiza com erro usando função de callback
      setApiKeys(prevKeys => prevKeys.map(k =>
        k.id === apiKey.id || (k.service === apiKey.service && k.key === apiKey.key)
          ? { ...k, status: errorStatus, checkingStatus: false }
          : k
      ));
    }
  };

  const syncCatalog = async () => {
    await modelCatalogApi.sync();
    await checkCatalogStatus();
  };

  return (
    <div className="api-key-manager">
      <div className="tabs-header" style={{
        display: 'flex',
        gap: '20px',
        marginBottom: '20px',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '10px'
      }}>
        <button
          className={`tab-btn ${activeTab === 'providers' ? 'active' : ''}`}
          onClick={() => setActiveTab('providers')}
          style={{
            padding: '8px 16px',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'providers' ? '2px solid var(--primary-color)' : 'none',
            color: activeTab === 'providers' ? 'var(--primary-color)' : 'var(--text-secondary)',
            fontWeight: 'bold',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          🔑 Chaves API
        </button>
        <button
          className={`tab-btn ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
          style={{
            padding: '8px 16px',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'models' ? '2px solid var(--primary-color)' : 'none',
            color: activeTab === 'models' ? 'var(--primary-color)' : 'var(--text-secondary)',
            fontWeight: 'bold',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          🧠 Modelos
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'providers' ? (
          <ProvidersTab
            apiKeys={apiKeys}
            services={SERVICES}
            onSave={handleSave}
            onDelete={handleDelete}
            onCheckStatus={checkApiKeyStatus}
          />
        ) : (
          <ModelsTab
            apiKeys={apiKeys}
            catalogStatus={catalogStatus}
            userPrefs={userPrefs}
            onSyncCatalog={syncCatalog}
          />
        )}
      </div>
    </div>
  );
};

