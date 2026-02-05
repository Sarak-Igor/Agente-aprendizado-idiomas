import { useState, useEffect } from 'react';
import { videoApi } from '../../services/api';
import { storage } from '../../services/storage';
import './KnowledgePractice.css';
import { SUPPORTED_PRACTICE_DIRECTIONS } from '../../config/languages';
import { usePracticeOrchestrator } from '../../hooks/usePracticeOrchestrator';

interface PracticePhrase {
  id: string;
  original: string;
  translated: string;
  source_language: string;
  target_language: string;
  video_title?: string;
  model_used?: string;
  service_used?: string;
}

interface PracticeStats {
  total: number;
  correct: number;
  incorrect: number;
  streak: number;
  skipped: number;
}

type PracticeMode = 'music-context' | 'new-context';
type TranslationDirection = 'en-to-pt' | 'pt-to-en';
type Difficulty = 'easy' | 'medium' | 'hard';

export const KnowledgePractice = () => {
  const [mode, setMode] = useState<PracticeMode>('music-context');
  const [direction, setDirection] = useState<TranslationDirection>('en-to-pt');
  const [selectedModes, setSelectedModes] = useState<PracticeMode[]>(['music-context','new-context']);
  const [selectedDirections, setSelectedDirections] = useState<TranslationDirection[]>(['en-to-pt','pt-to-en']);
  const orchestrator = usePracticeOrchestrator();
  const [sessionRunning, setSessionRunning] = useState(false);
  const [currentCategory, setCurrentCategory] = useState<{ mode: string; direction: string } | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty>('medium');
  const [currentPhrase, setCurrentPhrase] = useState<PracticePhrase | null>(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [showAnswer, setShowAnswer] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  // Carrega estatísticas do localStorage ao montar
  const loadStatsFromStorage = (): PracticeStats => {
    const saved = storage.getPracticeStats();
    if (saved) {
      return saved;
    }
    return {
      total: 0,
      correct: 0,
      incorrect: 0,
      streak: 0,
      skipped: 0,
    };
  };

  const [stats, setStats] = useState<PracticeStats>(loadStatsFromStorage());
  const [loading, setLoading] = useState(false);
  const [selectedVideos, setSelectedVideos] = useState<string[]>([]);
  const [availableVideos, setAvailableVideos] = useState<any[]>([]);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<{ service: string; model: string } | null>(null);
  const [availableAgents, setAvailableAgents] = useState<Array<{ service: string; model: string; display_name: string; available: boolean }>>([]);
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [customWords, setCustomWords] = useState<string[]>([]);

  useEffect(() => {
    loadAvailableVideos();
    loadAvailableAgents();
    // Carrega estatísticas salvas ao montar o componente
    const savedStats = storage.getPracticeStats();
    if (savedStats) {
      setStats(savedStats);
    }
    // Carrega frase não respondida se existir
    const savedPhrase = storage.getCurrentPhrase();
    if (savedPhrase && savedPhrase.phrase) {
      setCurrentPhrase(savedPhrase.phrase);
      setUserAnswer(savedPhrase.userAnswer);
    }
    // Carrega prompt padrão
    const defaultPrompt = `Você é um professor de idiomas. Crie uma frase natural e completa em {source_lang} usando TODAS as seguintes palavras: {words}

INSTRUÇÕES IMPORTANTES:
1. A frase deve ser natural, completa e fazer sentido gramaticalmente
2. Use TODAS as palavras fornecidas na frase
3. A frase deve ser adequada para nível {difficulty} de dificuldade ({difficulty_desc})
4. A frase deve ser uma sentença completa e coerente
5. NÃO adicione explicações, comentários ou prefixos como "Frase:" ou "A frase é:"
6. Retorne APENAS a frase criada, sem aspas, sem citações, sem nada além da frase

Exemplo de formato correto:
Se as palavras forem: ["love", "heart", "beautiful"]
Você deve retornar apenas: "I love your beautiful heart"

Agora crie a frase usando as palavras: {words}`;
    setCustomPrompt(defaultPrompt);
  }, []);

  // Salva frase não respondida sempre que mudar
  useEffect(() => {
    if (currentPhrase && !showAnswer && !userAnswer.trim()) {
      storage.saveCurrentPhrase(currentPhrase, userAnswer);
    } else if (showAnswer || userAnswer.trim()) {
      // Limpa se foi respondida
      storage.clearCurrentPhrase();
    }
  }, [currentPhrase, showAnswer, userAnswer]);

  const loadAvailableVideos = async () => {
    try {
      const response = await videoApi.listVideos();
      setAvailableVideos(response.videos || []);
    } catch (error) {
      console.error('Erro ao carregar vídeos:', error);
    }
  };

  const loadAvailableAgents = async () => {
    try {
      // Chaves de API agora são gerenciadas pelo backend (por usuário)
      // O backend busca automaticamente as chaves do usuário autenticado
      const apiKeys: { gemini?: string; openrouter?: string; groq?: string; together?: string } = {};
      
      console.log('Buscando agentes disponíveis (chaves gerenciadas pelo backend)...');
      const response = await videoApi.getAvailableAgents(apiKeys);
      console.log('Resposta completa do backend:', response);
      console.log('Agentes recebidos do backend:', response.agents);
      console.log('Número de agentes:', response.agents?.length || 0);
      
      if (response.agents && response.agents.length > 0) {
        setAvailableAgents(response.agents);
      } else {
        console.warn('Nenhum agente retornado do backend');
        setAvailableAgents([]);
      }
    } catch (error) {
      console.error('Erro ao carregar agentes disponíveis:', error);
      setAvailableAgents([]);
    }
  };

  const handleSelectAllVideos = (checked: boolean) => {
    if (checked) {
      setSelectedVideos(availableVideos.map(v => v.video_id));
    } else {
      setSelectedVideos([]);
    }
  };

  const loadNextPhrase = async () => {
    setLoading(true);
    setShowAnswer(false);
    setUserAnswer('');
    setIsCorrect(null);
    // Limpa frase salva ao carregar nova
    storage.clearCurrentPhrase();

    try {
      let phrase: PracticePhrase;

      if (mode === 'music-context') {
        // Modalidade 1: Frases das músicas
        phrase = await videoApi.getMusicPhrase({
          direction,
          difficulty,
          video_ids: selectedVideos.length > 0 ? selectedVideos : undefined,
        });
      } else {
        // Modalidade 2: Frases novas com palavras das músicas
        // Busca chaves de API do localStorage para enviar ao backend
        const apiKeys: { openrouter?: string; groq?: string; together?: string } = {};
        
        const openrouterKey = localStorage.getItem('openrouter_api_key');
        if (openrouterKey) apiKeys.openrouter = openrouterKey;
        
        const groqKey = localStorage.getItem('groq_api_key');
        if (groqKey) apiKeys.groq = groqKey;
        
        const togetherKey = localStorage.getItem('together_api_key');
        if (togetherKey) apiKeys.together = togetherKey;
        
        phrase = await videoApi.generatePracticePhrase({
          direction,
          difficulty,
          video_ids: selectedVideos.length > 0 ? selectedVideos : undefined,
          api_keys: Object.keys(apiKeys).length > 0 ? apiKeys : undefined,
          custom_prompt: customPrompt || undefined,
          preferred_agent: selectedAgent || undefined,
        });
      }

      // set currentCategory based on returned phrase languages (backend may have inverted)
      const src = phrase.source_language || direction;
      const tgt = phrase.target_language || (direction === 'en-to-pt' ? 'pt' : 'en');
      const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
      setCurrentCategory({ mode: mode, direction: effectiveDirection });
      setCurrentPhrase(phrase);
      // Salva frase não respondida
      storage.saveCurrentPhrase(phrase, '');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Erro ao carregar frase. Verifique se há vídeos traduzidos.');
    } finally {
      setLoading(false);
    }
  };

  // Orchestrator-based flow (round-robin). Start session using selectedModes/selectedDirections
  const startSession = async () => {
    if (!selectedModes || selectedModes.length === 0) {
      alert('Selecione ao menos uma modalidade.');
      return;
    }
    if (!selectedDirections || selectedDirections.length === 0) {
      alert('Selecione ao menos uma direção.');
      return;
    }
    console.debug('Starting session with', { selectedModes, selectedDirections, difficulty, selectedVideos });
    orchestrator.start(selectedModes as any, selectedDirections as any, difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
    setSessionRunning(true);
    // fetch first item
    const item = await orchestrator.next(difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
    if (item) {
      // derive effective direction from payload (backend may have inverted)
      const src = item.payload.source_language || item.direction?.split('-')[0] || 'en';
      const tgt = item.payload.target_language || item.direction?.split('-')[1] || 'pt';
      const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
      setCurrentCategory({ mode: item.mode, direction: effectiveDirection });
      setCurrentPhrase(item.payload);
      setShowAnswer(false);
      setUserAnswer('');
      setIsCorrect(null);
    } else {
      alert('Não foi possível obter exercícios com as opções selecionadas.');
    }
  };

  const stopSession = () => {
    orchestrator.stop();
    setSessionRunning(false);
    setCurrentCategory(null);
  };

  const nextSessionItem = async () => {
    if (!sessionRunning) {
      // fallback to previous behavior
      await loadNextPhrase();
      return;
    }
    try {
      const item = await orchestrator.next(difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
      if (item) {
        const src = item.payload.source_language || item.direction?.split('-')[0] || 'en';
        const tgt = item.payload.target_language || item.direction?.split('-')[1] || 'pt';
        const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
        setCurrentCategory({ mode: item.mode, direction: effectiveDirection });
        setCurrentPhrase(item.payload);
        setShowAnswer(false);
        setUserAnswer('');
        setIsCorrect(null);
      } else {
        // Could not fetch any combo after trying all combos
        alert('Não há mais exercícios disponíveis no momento para as opções selecionadas. A sessão será encerrada.');
        stopSession();
      }
    } catch (err) {
      console.error('Erro ao obter próximo exercício do orquestrador:', err);
      // Try one more time; if still fails, stop session.
      try {
        const item = await orchestrator.next(difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
        if (item) {
          const src = item.payload.source_language || item.direction?.split('-')[0] || 'en';
          const tgt = item.payload.target_language || item.direction?.split('-')[1] || 'pt';
          const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
          setCurrentCategory({ mode: item.mode, direction: effectiveDirection });
          setCurrentPhrase(item.payload);
          setShowAnswer(false);
          setUserAnswer('');
          setIsCorrect(null);
          return;
        }
      } catch (err2) {
        console.error('Segunda tentativa falhou:', err2);
      }
      alert('Erro ao obter próximo exercício. A sessão será encerrada.');
      stopSession();
    }
  };

  // word-related flows removed (Palavra mode was disabled per request)

  const checkAnswer = async () => {
    if (!currentPhrase || !userAnswer.trim()) {
      return;
    }

    // Validação adicional
    if (!currentPhrase.id) {
      alert('Erro: ID da frase não encontrado. Recarregue a frase.');
      return;
    }

    try {
      const effectiveDirection = currentCategory ? (currentCategory.direction as string) : direction;
      // Para frases geradas, precisa enviar a resposta correta também
      const checkParams: any = {
        phrase_id: currentPhrase.id,
        user_answer: userAnswer.trim(),
        direction: effectiveDirection,
      };
      
      // Se for frase gerada, adiciona resposta correta
      if (currentPhrase.id && currentPhrase.id.startsWith('generated-')) {
        const correctAnswer = effectiveDirection === 'en-to-pt' 
          ? currentPhrase.translated 
          : currentPhrase.original;
        
        if (!correctAnswer) {
          alert('Erro: Resposta correta não encontrada. Recarregue a frase.');
          return;
        }
        
        checkParams.correct_answer = correctAnswer;
      }
      
      const result = await videoApi.checkPracticeAnswer(checkParams);

      setIsCorrect(result.is_correct);
      setShowAnswer(true);
      updateStats(result.is_correct);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Erro ao verificar resposta';
      console.error('Erro ao verificar resposta:', error);
      alert(errorMessage);
    }
  };

  const updateStats = (correct: boolean) => {
    setStats((prev) => {
      const newStats = {
        total: prev.total + 1,
        correct: correct ? prev.correct + 1 : prev.correct,
        incorrect: correct ? prev.incorrect : prev.incorrect + 1,
        streak: correct ? prev.streak + 1 : 0,
        skipped: prev.skipped || 0,
      };
      // Salva no localStorage sempre que atualizar
      storage.setPracticeStats(newStats);
      // Limpa frase salva quando responde
      if (currentPhrase) {
        storage.clearCurrentPhrase();
      }
      return newStats;
    });
  };

  const skipPhrase = () => {
    setStats((prev) => {
      const newStats = {
        total: prev.total,
        correct: prev.correct,
        incorrect: prev.incorrect,
        streak: 0, // Reseta sequência ao pular
        skipped: (prev.skipped || 0) + 1,
      };
      // Salva no localStorage
      storage.setPracticeStats(newStats);
      return newStats;
    });
    
    // Limpa frase atual e carrega próxima (usa orquestrador se sessão ativa)
    setShowAnswer(false);
    setUserAnswer('');
    setIsCorrect(null);
    storage.clearCurrentPhrase();
    
    if (sessionRunning) {
      nextSessionItem();
    } else {
      loadNextPhrase();
    }
  };

  const saveSession = () => {
    if (stats.total === 0) {
      alert('Não há estatísticas para salvar. Pratique primeiro!');
      return;
    }

    const session = {
      ...stats,
      skipped: stats.skipped || 0,
      timestamp: new Date().toISOString(),
    };

    storage.savePracticeSession(session);
    alert(`Sessão salva com sucesso!\n\nTotal: ${stats.total}\nAcertos: ${stats.correct}\nErros: ${stats.incorrect}\nPuladas: ${stats.skipped || 0}\nSequência: ${stats.streak}`);
  };

  const resetStats = () => {
    const resetStats = {
      total: 0,
      correct: 0,
      incorrect: 0,
      streak: 0,
      skipped: 0,
    };
    setStats(resetStats);
    // Limpa do localStorage também
    storage.clearPracticeStats();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !showAnswer) {
      checkAnswer();
    } else if (e.key === 'Enter' && showAnswer) {
      loadNextPhrase();
    }
  };

  const getModelDisplayName = (model: string, service?: string): string => {
    if (!model) return 'Desconhecido';
    
    // Nomes amigáveis para os modelos
    const modelNames: { [key: string]: string } = {
      'gemini-1.5-flash': 'Gemini 1.5 Flash',
      'gemini-1.5-pro': 'Gemini 1.5 Pro',
      'gemini-2.0-flash': 'Gemini 2.0 Flash',
      'gemini-2.5-flash': 'Gemini 2.5 Flash',
      'gemini-2.5-pro': 'Gemini 2.5 Pro',
      'openai/gpt-3.5-turbo': 'GPT-3.5 Turbo (OpenRouter)',
      'llama-3.1-8b-instant': 'Llama 3.1 8B (Groq)',
      'meta-llama/Llama-3-8b-chat-hf': 'Llama 3 8B (Together AI)',
    };
    
    // Se tiver nome amigável, usa ele
    if (modelNames[model]) {
      return modelNames[model];
    }
    
    // Caso contrário, formata o nome
    if (service) {
      const serviceNames: { [key: string]: string } = {
        'gemini': 'Gemini',
        'openrouter': 'OpenRouter',
        'groq': 'Groq',
        'together': 'Together AI'
      };
      return `${model} (${serviceNames[service] || service})`;
    }
    
    return model;
  };

  return (
    <div className="knowledge-practice">
      <div className="practice-header">
        <h2>📚 Treinar idioma</h2>
        <p>Use as letras das músicas traduzidas para praticar e treinar o idioma</p>
      </div>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '12px' }}>
        {!sessionRunning ? (
          <button onClick={startSession} className="start-btn" style={{ padding: '8px 12px' }}>
            ▶️ Iniciar Sessão (multiseleção)
          </button>
        ) : (
          <button onClick={stopSession} className="start-btn" style={{ padding: '8px 12px', background: '#e74c3c' }}>
            ⏹️ Encerrar Sessão
          </button>
        )}
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          {sessionRunning ? 'Sessão ativa — perguntas serão intercaladas entre as seleções.' : 'Sessão inativa'}
        </div>
      </div>

      <div className="practice-config">
        <div className="config-section">
          <label>Modalidade (selecione uma ou mais):</label>
          <div className="checkbox-group">
            <label>
              <input
                type="checkbox"
                value="music-context"
                checked={selectedModes.includes('music-context')}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSelectedModes((prev) => {
                    if (checked) return [...prev, 'music-context'];
                    return prev.filter((p) => p !== 'music-context');
                  });
                }}
              />
              <span>Frases das Músicas</span>
            </label>
            <label>
              <input
                type="checkbox"
                value="new-context"
                checked={selectedModes.includes('new-context')}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSelectedModes((prev) => {
                    if (checked) return [...prev, 'new-context'];
                    return prev.filter((p) => p !== 'new-context');
                  });
                }}
              />
              <span>Frases com Novo Contexto</span>
            </label>
          </div>
        </div>
        {/* Palavra config removed */}

        {/* Palavra exercise removed */}

        <div className="config-section">
          <label>Direção da Tradução (selecione uma ou mais):</label>
          <div className="checkbox-group">
            {SUPPORTED_PRACTICE_DIRECTIONS.map((dir) => {
              const label = dir === 'en-to-pt' ? 'Inglês → Português' : dir === 'pt-to-en' ? 'Português → Inglês' : dir;
              return (
                <label key={dir}>
                  <input
                    type="checkbox"
                    value={dir}
                    checked={selectedDirections.includes(dir as any)}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setSelectedDirections((prev) => {
                        if (checked) return [...prev, dir as TranslationDirection];
                        return prev.filter((d) => d !== dir);
                      });
                    }}
                  />
                  <span>{label}</span>
                </label>
              );
            })}
          </div>
        </div>

        <div className="config-section">
          <label>Dificuldade:</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as Difficulty)}
          >
            <option value="easy">Fácil</option>
            <option value="medium">Médio</option>
            <option value="hard">Difícil</option>
          </select>
        </div>

        <div className="config-section">
          <div className="config-section-header">
            <label>Vídeos (opcional - deixe vazio para usar todos):</label>
            <button 
              onClick={() => {
                setShowConfigModal(true);
                loadAvailableAgents();
              }} 
              className="config-btn"
              title="Configurar prompt e agente"
            >
              ⚙️ Configurações
            </button>
          </div>
          <div className="video-selector">
            {availableVideos.length > 0 && (
              <label className="video-checkbox select-all">
                <input
                  type="checkbox"
                  checked={selectedVideos.length === availableVideos.length && availableVideos.length > 0}
                  onChange={(e) => handleSelectAllVideos(e.target.checked)}
                />
                <span><strong>Selecionar todos</strong></span>
              </label>
            )}
            {availableVideos.map((video) => (
              <label key={video.video_id} className="video-checkbox">
                <input
                  type="checkbox"
                  checked={selectedVideos.includes(video.video_id)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedVideos([...selectedVideos, video.video_id]);
                    } else {
                      setSelectedVideos(selectedVideos.filter((id) => id !== video.video_id));
                    }
                  }}
                />
                <span>{video.title}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="practice-stats">
        <div className="stat-item">
          <span className="stat-label">Total:</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Acertos:</span>
          <span className="stat-value correct">{stats.correct}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Erros:</span>
          <span className="stat-value incorrect">{stats.incorrect}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Sequência:</span>
          <span className="stat-value streak">{stats.streak}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Puladas:</span>
          <span className="stat-value skipped">{stats.skipped || 0}</span>
        </div>
        <button onClick={resetStats} className="reset-stats-btn">
          Resetar
        </button>
        <button onClick={saveSession} className="save-session-btn" title="Salvar sessão atual">
          💾 Salvar Sessão
        </button>
      </div>

      <div className="practice-exercise">
        {mode === 'new-context' && customWords.length > 0 && !loading && (
          <div className="exercise-content">
            <div className="phrase-display">
              <div className="phrase-label">
                {direction === 'en-to-pt' ? 'Traduza a palavra do Inglês:' : 'Traduza a palavra do Português:'}
              </div>
              <div className="phrase-text word-text">
                {customWords[currentWordIndex]}
              </div>
              <div className="word-progress">
                Palavra {currentWordIndex + 1} de {customWords.length}
              </div>
            </div>

            <div className="answer-section">
              <label>Sua tradução:</label>
              <input
                type="text"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !showAnswer) {
                    checkWordTranslation(customWords[currentWordIndex], userAnswer);
                  } else if (e.key === 'Enter' && showAnswer) {
                    loadNextWord();
                  }
                }}
                placeholder="Digite a tradução aqui..."
                disabled={showAnswer}
                className="word-answer-input"
              />

              {!showAnswer && (
                <div className="action-buttons">
                  <button 
                    onClick={() => checkWordTranslation(customWords[currentWordIndex], userAnswer)} 
                    className="check-btn" 
                    disabled={!userAnswer.trim()}
                  >
                    Verificar
                  </button>
                  <button onClick={skipPhrase} className="skip-btn" title="Pular esta palavra">
                    ⏭️ Pular
                  </button>
                </div>
              )}

              {showAnswer && (
                <div className={`answer-feedback ${isCorrect ? 'correct' : 'incorrect'}`}>
                  <div className="feedback-header">
                    {isCorrect ? '✅ Correto!' : '❌ Incorreto'}
                  </div>
                  {wordTranslations[customWords[currentWordIndex]] && (
                    <div className="correct-answer">
                      <strong>Tradução correta:</strong>
                      <div className="answer-text">
                        {wordTranslations[customWords[currentWordIndex]]}
                      </div>
                    </div>
                  )}
                  <button onClick={loadNextWord} className="next-btn">
                    {currentWordIndex < customWords.length - 1 ? 'Próxima Palavra' : 'Recomeçar'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {mode === 'new-context' && customWords.length === 0 && !loading && (
          <div className="exercise-placeholder">
            <p>Adicione palavras acima para começar a praticar!</p>
          </div>
        )}

        {!currentPhrase && !loading && (
          <div className="exercise-placeholder">
            <p>Clique em "Iniciar" para começar a praticar!</p>
            {!sessionRunning ? (
              <button onClick={startSession} className="start-btn">
                Iniciar
              </button>
            ) : (
              <button onClick={stopSession} className="start-btn">
                Encerrar Sessão
              </button>
            )}
          </div>
        )}

        {loading && (
          <div className="exercise-loading">
            <p>Carregando frase...</p>
          </div>
        )}

        {currentPhrase && !loading && (
          <div className="exercise-content">
            <div className="phrase-display">
              <div className="category-label" style={{ marginBottom: '8px', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                {currentCategory ? `Modo: ${currentCategory.mode === 'music-context' ? 'Frases das Músicas' : 'Frases com Novo Contexto'} — Direção: ${currentCategory.direction === 'en-to-pt' ? 'Inglês → Português' : 'Português → Inglês'}` : (direction === 'en-to-pt' ? 'Traduza do Inglês:' : 'Traduza do Português:')}
              </div>
              <div className="phrase-text">
                {/* Mostrar apenas o texto de origem para o exercício; revelar tradução apenas após resposta */}
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '1.25rem', marginTop: '6px' }}>
                    {currentPhrase.original}
                  </div>
                </div>

                {showAnswer && (
                  <div style={{ marginTop: '8px', color: 'var(--text-secondary)' }}>
                    <strong>Tradução:</strong>
                    <div style={{ fontStyle: 'italic', marginTop: '6px' }}>{currentPhrase.translated}</div>
                  </div>
                )}
              </div>
              {currentPhrase.video_title && (
                <div className="phrase-source">Música: {currentPhrase.video_title}</div>
              )}
              {currentPhrase.model_used && (
                <div className="phrase-model">
                  <span className="model-label">Modelo usado:</span>
                  <span className="model-name">{getModelDisplayName(currentPhrase.model_used, currentPhrase.service_used)}</span>
                </div>
              )}
            </div>

            <div className="answer-section">
              <label>Sua resposta:</label>
              <textarea
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua tradução aqui..."
                disabled={showAnswer}
                className="answer-input"
              />

              {!showAnswer && (
                <div className="action-buttons">
                  <button onClick={checkAnswer} className="check-btn" disabled={!userAnswer.trim()}>
                    Verificar
                  </button>
                  <button onClick={skipPhrase} className="skip-btn" title="Pular esta frase">
                    ⏭️ Pular
                  </button>
                </div>
              )}

              {showAnswer && (
                <div className={`answer-feedback ${isCorrect ? 'correct' : 'incorrect'}`}>
                  <div className="feedback-header">
                    {isCorrect ? '✅ Correto!' : '❌ Incorreto'}
                  </div>
                  <div className="correct-answer">
                    <strong>Resposta correta:</strong>
                    <div className="answer-text">
                      {direction === 'en-to-pt' ? currentPhrase.translated : currentPhrase.original}
                    </div>
                  </div>
                  {!isCorrect && (
                    <div className="user-answer">
                      <strong>Sua resposta:</strong>
                      <div className="answer-text">{userAnswer}</div>
                    </div>
                  )}
                  <button onClick={loadNextPhrase} className="next-btn">
                    Próxima Frase
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal de Configuração */}
      {showConfigModal && (
        <div className="modal-overlay" onClick={() => setShowConfigModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>⚙️ Configurações de Geração</h3>
              <button className="modal-close" onClick={() => setShowConfigModal(false)}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="config-field">
                <label>Prompt Customizado:</label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Digite o prompt customizado aqui..."
                  className="prompt-textarea"
                  rows={12}
                />
                <div className="prompt-help">
                  <strong>Placeholders disponíveis:</strong>
                  <ul>
                    <li><code>{'{words}'}</code> - Palavras selecionadas</li>
                    <li><code>{'{source_lang}'}</code> - Idioma de origem</li>
                    <li><code>{'{target_lang}'}</code> - Idioma de destino</li>
                    <li><code>{'{difficulty}'}</code> - Nível de dificuldade</li>
                    <li><code>{'{difficulty_desc}'}</code> - Descrição da dificuldade</li>
                  </ul>
                </div>
              </div>

              <div className="config-field">
                <label>Agente Preferido (opcional):</label>
                <select
                  value={selectedAgent ? `${selectedAgent.service}:${selectedAgent.model}` : ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value) {
                      const [service, model] = value.split(':');
                      setSelectedAgent({ service, model });
                    } else {
                      setSelectedAgent(null);
                    }
                  }}
                  className="agent-select"
                >
                  <option value="">Usar agente automático (fallback)</option>
                  {availableAgents && availableAgents.length > 0 ? (
                    availableAgents
                      .filter(a => a.available !== false)
                      .map((agent) => (
                        <option key={`${agent.service}:${agent.model}`} value={`${agent.service}:${agent.model}`}>
                          {agent.display_name}
                        </option>
                      ))
                  ) : (
                    <option value="" disabled>Carregando agentes...</option>
                  )}
                </select>
                {(!availableAgents || availableAgents.length === 0) && (
                  <p className="no-agents">Nenhum agente disponível. Configure chaves de API na aba "Modelos LLM" e verifique as cotas.</p>
                )}
                {availableAgents && availableAgents.length > 0 && (
                  <p className="agents-info" style={{ marginTop: '8px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {availableAgents.length} agente(s) disponível(is)
                  </p>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button onClick={() => setShowConfigModal(false)} className="modal-btn-primary">
                Salvar
              </button>
              <button 
                onClick={() => {
                  const defaultPrompt = `Você é um professor de idiomas. Crie uma frase natural e completa em {source_lang} usando TODAS as seguintes palavras: {words}

INSTRUÇÕES IMPORTANTES:
1. A frase deve ser natural, completa e fazer sentido gramaticalmente
2. Use TODAS as palavras fornecidas na frase
3. A frase deve ser adequada para nível {difficulty} de dificuldade ({difficulty_desc})
4. A frase deve ser uma sentença completa e coerente
5. NÃO adicione explicações, comentários ou prefixos como "Frase:" ou "A frase é:"
6. Retorne APENAS a frase criada, sem aspas, sem citações, sem nada além da frase

Exemplo de formato correto:
Se as palavras forem: ["love", "heart", "beautiful"]
Você deve retornar apenas: "I love your beautiful heart"

Agora crie a frase usando as palavras: {words}`;
                  setCustomPrompt(defaultPrompt);
                  setSelectedAgent(null);
                }} 
                className="modal-btn-secondary"
              >
                Restaurar Padrão
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
