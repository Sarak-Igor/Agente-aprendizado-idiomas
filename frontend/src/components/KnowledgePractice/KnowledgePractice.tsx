import { useState, useEffect } from 'react';
import { videoApi } from '../../services/api';
import { storage } from '../../services/storage';
import './KnowledgePractice.css';
import { SUPPORTED_PRACTICE_DIRECTIONS } from '../../config/languages';
import { usePracticeOrchestrator } from '../../hooks/usePracticeOrchestrator';
import ClozeExercise from '../ClozeExercise/ClozeExercise';
import SentenceScramble from './SentenceScramble';
import { useTheme } from '../../contexts/ThemeContext';

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

type PracticeMode = 'music-context' | 'new-context' | 'cloze' | 'sentence-scramble';
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
  const [currentCloze, setCurrentCloze] = useState<any | null>(null);
  const [currentScramble, setCurrentScramble] = useState<any | null>(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [showAnswer, setShowAnswer] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const loadStatsFromStorage = (): PracticeStats => {
    const saved = storage.getPracticeStats();
    if (saved) return saved;
    return { total: 0, correct: 0, incorrect: 0, streak: 0, skipped: 0 };
  };

  const [stats, setStats] = useState<PracticeStats>(loadStatsFromStorage());
  const [loading, setLoading] = useState(false);
  const [selectedVideos, setSelectedVideos] = useState<string[]>([]);
  const [availableVideos, setAvailableVideos] = useState<any[]>([]);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showDirectionPopover, setShowDirectionPopover] = useState(false);
  const [tempSelectedVideos, setTempSelectedVideos] = useState<string[] | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<{ service: string; model: string } | null>(null);
  const [availableAgents, setAvailableAgents] = useState<Array<{ service: string; model: string; display_name: string; available: boolean }>>([]);
  // local UI states for enhanced layout
  const [selectedSession, setSelectedSession] = useState<any | null>(null);
  const [showSessionDetail, setShowSessionDetail] = useState(false);

  useEffect(() => {
    (async () => {
      if ((videoApi as any).getAvailableVideos) {
        try {
          const vids = await (videoApi as any).getAvailableVideos();
          setAvailableVideos(vids || []);
        } catch (e) { /* ignore */ }
      }
    })();

    const savedStats = storage.getPracticeStats();
    if (savedStats) setStats(savedStats);
    const savedPhrase = storage.getCurrentPhrase();
    if (savedPhrase && savedPhrase.phrase) {
      setCurrentPhrase(savedPhrase.phrase);
      setUserAnswer(savedPhrase.userAnswer);
    }
    const defaultPrompt = `Você é um professor de idiomas. Crie uma frase natural e completa em {source_lang} usando TODAS as seguintes palavras: {words}`;
    setCustomPrompt(defaultPrompt);
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showVideoModal) setShowVideoModal(false);
        if (showDirectionPopover) setShowDirectionPopover(false);
        if (showConfigModal) setShowConfigModal(false);
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showVideoModal, showDirectionPopover, showConfigModal]);

  const loadCloze = async (gaps = 1) => {
    setLoading(true);
    setCurrentCloze(null);
    setCurrentPhrase(null);
    setCurrentScramble(null);
    try {
      const resp = await videoApi.getCloze({
        mode, direction, difficulty, gaps,
        video_ids: selectedVideos.length > 0 ? selectedVideos : undefined,
      });
      setCurrentCloze(resp);
      setShowAnswer(false);
      setUserAnswer('');
      setIsCorrect(null);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erro ao carregar exercício Cloze');
    } finally { setLoading(false); }
  };

  const handleCheckCloze = async (answers: string[]) => {
    if (!currentCloze) return { is_correct: false };
    try {
      const resp = await videoApi.checkCloze({ phrase_id: currentCloze.id, answers, expected_answers: currentCloze.answers, direction });
      setShowAnswer(true);
      setIsCorrect(resp.is_correct);
      return resp;
    } catch (e) {
      alert('Erro ao verificar cloze');
      return { is_correct: false };
    }
  };

  const startSession = async () => {
    if (!selectedModes || selectedModes.length === 0) { alert('Selecione ao menos uma modalidade.'); return; }
    if (!selectedDirections || selectedDirections.length === 0) { alert('Selecione ao menos uma direção.'); return; }
    orchestrator.start(selectedModes as any, selectedDirections as any, difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
    setSessionRunning(true);
    const item = await orchestrator.next(difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
    if (item) {
      const src = item.payload.source_language || item.direction?.split('-')[0] || 'en';
      const tgt = item.payload.target_language || item.direction?.split('-')[1] || 'pt';
      const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
      setCurrentCategory({ mode: item.mode, direction: effectiveDirection });
      setCurrentCloze(null); setCurrentPhrase(null); setCurrentScramble(null);
      if (item.mode === 'cloze') setCurrentCloze(item.payload);
      else if (item.mode === 'sentence-scramble') setCurrentScramble(item.payload);
      else setCurrentPhrase(item.payload);
      setShowAnswer(false); setUserAnswer(''); setIsCorrect(null);
    } else {
      alert('Não foi possível obter exercícios com as opções selecionadas.');
    }
  };

  const stopSession = () => {
    orchestrator.stop();
    setSessionRunning(false);
    setCurrentCategory(null); setCurrentCloze(null); setCurrentPhrase(null); setCurrentScramble(null);
  };

  const nextSessionItem = async () => {
    if (!sessionRunning) { /* fallback */ return; }
    try {
      const item = await orchestrator.next(difficulty, selectedVideos.length > 0 ? selectedVideos : undefined, undefined, customPrompt || undefined, selectedAgent || undefined);
      if (item) {
        const src = item.payload.source_language || item.direction?.split('-')[0] || 'en';
        const tgt = item.payload.target_language || item.direction?.split('-')[1] || 'pt';
        const effectiveDirection = src === 'en' && tgt === 'pt' ? 'en-to-pt' : 'pt-to-en';
        setCurrentCategory({ mode: item.mode, direction: effectiveDirection });
        setCurrentCloze(null); setCurrentPhrase(null); setCurrentScramble(null);
        if (item.mode === 'cloze') setCurrentCloze(item.payload);
        else if (item.mode === 'sentence-scramble') setCurrentScramble(item.payload);
        else setCurrentPhrase(item.payload);
        setShowAnswer(false); setUserAnswer(''); setIsCorrect(null);
      } else {
        alert('Não há mais exercícios disponíveis no momento para as opções selecionadas. A sessão será encerrada.');
        stopSession();
      }
    } catch (err) {
      console.error(err);
      alert('Erro ao obter próximo exercício. A sessão será encerrada.');
      stopSession();
    }
  };

  const checkAnswer = async () => {
    if (!currentPhrase || !userAnswer.trim()) return;
    if (!currentPhrase.id) { alert('Erro: ID da frase não encontrado. Recarregue a frase.'); return; }
    try {
      const effectiveDirection = currentCategory ? (currentCategory.direction as string) : direction;
      const checkParams: any = { phrase_id: currentPhrase.id, user_answer: userAnswer.trim(), direction: effectiveDirection };
      if (currentPhrase.id && currentPhrase.id.startsWith('generated-')) {
        const correctAnswer = effectiveDirection === 'en-to-pt' ? currentPhrase.translated : currentPhrase.original;
        if (!correctAnswer) { alert('Erro: Resposta correta não encontrada. Recarregue a frase.'); return; }
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
      const newStats = { total: prev.total + 1, correct: correct ? prev.correct + 1 : prev.correct, incorrect: correct ? prev.incorrect : prev.incorrect + 1, streak: correct ? prev.streak + 1 : 0, skipped: prev.skipped || 0 };
      storage.setPracticeStats(newStats);
      if (currentPhrase) storage.clearCurrentPhrase();
      return newStats;
    });
  };

  const skipPhrase = () => {
    setStats((prev) => {
      const newStats = { total: prev.total, correct: prev.correct, incorrect: prev.incorrect, streak: 0, skipped: (prev.skipped || 0) + 1 };
      storage.setPracticeStats(newStats);
      return newStats;
    });
    setShowAnswer(false); setUserAnswer(''); setIsCorrect(null); storage.clearCurrentPhrase();
    if (sessionRunning) nextSessionItem();
  };

  const saveSession = () => {
    if (stats.total === 0) { alert('Não há estatísticas para salvar. Pratique primeiro!'); return; }
    const session = { ...stats, skipped: stats.skipped || 0, timestamp: new Date().toISOString() };
    storage.savePracticeSession(session);
    alert(`Sessão salva com sucesso!\n\nTotal: ${stats.total}\nAcertos: ${stats.correct}\nErros: ${stats.incorrect}\nPuladas: ${stats.skipped || 0}\nSequência: ${stats.streak}`);
  };

  const resetStats = () => {
    const resetStats = { total: 0, correct: 0, incorrect: 0, streak: 0, skipped: 0 };
    setStats(resetStats);
    storage.clearPracticeStats();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !showAnswer) checkAnswer();
    else if (e.key === 'Enter' && showAnswer) nextSessionItem();
  };

  const getModelDisplayName = (model: string, service?: string): string => {
    if (!model) return 'Desconhecido';
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
    if (modelNames[model]) return modelNames[model];
    if (service) {
      const serviceNames: { [key: string]: string } = { 'gemini': 'Gemini', 'openrouter': 'OpenRouter', 'groq': 'Groq', 'together': 'Together AI' };
      return `${model} (${serviceNames[service] || service})`;
    }
    return model;
  };

  const { theme, toggleTheme } = useTheme();

  return (
    <div className="knowledge-practice">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div>
          <h2 style={{ margin: 0 }}>Treinar Inglês — Exemplo</h2>
          <div className="small">Protótipo com seleção de modalidades, vídeos, direção e histórico</div>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="small">Tema</div>
            <button className="ghost" onClick={toggleTheme}>{theme === 'light' ? 'Claro' : 'Escuro'}</button>
          </div>
          <div className="small muted">Usuário: Exemplo</div>
        </div>
      </header>

      <main className="app layout" role="main" style={{ gap: 24 }}>
        <aside className="card panel left" aria-labelledby="left-title">
          <h3 id="left-title">Modalidades de exercício</h3>
          <div className="modes" id="modes" style={{ marginTop: 8 }}>
            <label className="mode" style={{ display: 'block', cursor: 'pointer' }}>
              <input type="checkbox" checked={selectedModes.includes('music-context')} onChange={() => {
                setSelectedModes((prev) => prev.includes('music-context') ? prev.filter(m => m !== 'music-context') : [...prev, 'music-context']);
              }} /> <strong style={{ marginLeft: 8 }}>Frases de músicas</strong>
              <div className="small" style={{ marginLeft: 26 }}>Contexto real</div>
            </label>
            <label className="mode" style={{ display: 'block', cursor: 'pointer' }}>
              <input type="checkbox" checked={selectedModes.includes('new-context')} onChange={() => {
                setSelectedModes((prev) => prev.includes('new-context') ? prev.filter(m => m !== 'new-context') : [...prev, 'new-context']);
              }} /> <strong style={{ marginLeft: 8 }}>Cloze (lacunas)</strong>
              <div className="small" style={{ marginLeft: 26 }}>Complete as frases</div>
            </label>
            <label className="mode" style={{ display: 'block', cursor: 'pointer' }}>
              <input type="checkbox" checked={selectedModes.includes('sentence-scramble')} onChange={() => {
                setSelectedModes((prev) => prev.includes('sentence-scramble') ? prev.filter(m => m !== 'sentence-scramble') : [...prev, 'sentence-scramble']);
              }} /> <strong style={{ marginLeft: 8 }}>Sentence Scramble</strong>
              <div className="small" style={{ marginLeft: 26 }}>Ordene as palavras</div>
            </label>
            <label className="mode" style={{ display: 'block', cursor: 'pointer' }}>
              <input type="checkbox" checked={selectedModes.includes('cloze')} onChange={() => {
                setSelectedModes((prev) => prev.includes('cloze') ? prev.filter(m => m !== 'cloze') : [...prev, 'cloze']);
              }} /> <strong style={{ marginLeft: 8 }}>Tradução livre</strong>
              <div className="small" style={{ marginLeft: 26 }}>Traduza sentenças</div>
            </label>
          </div>

          <hr style={{ margin: '12px 0', opacity: 0.06 }} />

          <h3>Vídeos base</h3>
          <div className="small">Selecione os vídeos que servirão de base para extrair frases.</div>
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            <button id="chooseVideos" className="ghost" onClick={() => setShowVideoModal(true)}>Escolher vídeos</button>
            <button id="clearVideos" className="ghost" onClick={() => setSelectedVideos([])}>Limpar</button>
          </div>

          <div style={{ marginTop: 12 }}>
            <h3>Direção</h3>
            <div className="small" id="directionDesc">{selectedDirections[0] === 'pt-to-en' ? 'Português → Inglês' : 'Inglês → Português'}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button id="dirConfirm" className="ghost" onClick={() => alert('Direção confirmada')}>Confirmar direção</button>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <h3>Dificuldade</h3>
            <select id="difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)} style={{ width: '100%', padding: 10, borderRadius: 8 }}>
              <option value="easy">Fácil</option>
              <option value="medium">Médio</option>
              <option value="hard">Difícil</option>
            </select>
          </div>

          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div className="stat-item"><div className="small">Total</div><div className="stat-value">{stats.total}</div></div>
              <div className="stat-item"><div className="small">Acertos</div><div className="stat-value correct">{stats.correct}</div></div>
              <div className="stat-item"><div className="small">Erros</div><div className="stat-value incorrect">{stats.incorrect}</div></div>
              <div className="stat-item"><div className="small">Sequência</div><div className="stat-value streak">{stats.streak}</div></div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
            <button className="btn" onClick={startSession}>Iniciar sessão</button>
            <button className="btn ghost" onClick={saveSession}>Salvar sessão</button>
            <button className="btn ghost" onClick={resetStats}>Resetar</button>
          </div>
        </aside>

        <section className="session-area" aria-labelledby="session-title">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 id="session-title" style={{ margin: 0 }}>Sessão ativa</h2>
            <div className="small muted" id="sessionSummary">Sessão: {sessionRunning ? 'ativa' : '—'} • {stats.total} perguntas • {stats.correct} corretas</div>
          </div>

          <div className="card panel exercise" id="activeSession" aria-live="polite">
            <div className="top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="badge">{currentCategory?.mode ? currentCategory.mode : '—'}</span>
                <span style={{ marginLeft: 8, fontSize: 14, color: 'var(--muted)' }}>{/* placeholder for index */}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="small">Tempo</div>
                  <div style={{ fontWeight: 800 }} id="questionTimer">00:30</div>
                </div>
                <button id="playAudio" className="btn ghost" onClick={() => alert('Tocar áudio (exemplo)')}>🔊</button>
                <button id="showHint" className="btn secondary" onClick={() => alert('Dica: pense no verbo certo')}>💡 Dica</button>
              </div>
            </div>

            <div className="phrase" id="phraseText">{currentPhrase ? currentPhrase.original : 'Nenhuma sessão ativa. Configure as opções e clique em "Iniciar sessão".'}</div>
            <div className="metaRow">
              <div id="phraseMeta" className="small">{currentPhrase?.video_title ? `Fonte: ${currentPhrase.video_title}` : ''}</div>
              <div id="sourceBadge" className="small muted">{currentPhrase?.source_language || ''}</div>
            </div>

            <div className="progressBar" style={{ marginBottom: 10 }}><i id="progressFill" style={{ width: `${Math.min(100, (stats.total / Math.max(1, 10)) * 100)}%` }}></i></div>

            {currentCloze ? (
              <ClozeExercise cloze={currentCloze} onCheck={handleCheckCloze} />
            ) : currentScramble ? (
              <SentenceScramble initialItem={currentScramble} direction={direction} difficulty={difficulty} onAnswered={(c) => updateStats(!!c)} onNext={() => nextSessionItem()} />
            ) : currentPhrase ? (
              <>
                <textarea className="answer" value={userAnswer} onChange={(e) => setUserAnswer(e.target.value)} disabled={showAnswer} onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); checkAnswer(); }
                }} />
                <div className="controls">
                  <button className="btn ghost" onClick={checkAnswer} disabled={!userAnswer.trim()}>Verificar</button>
                  <button className="btn secondary" onClick={skipPhrase}>Pular</button>
                </div>
              </>
            ) : (
              <div className="small muted" style={{ textAlign: 'center', padding: 20 }}>Nenhuma sessão ativa. Selecione as opções à esquerda e clique em "Iniciar sessão".</div>
            )}

            <div className="statsRow" style={{ marginTop: 12 }}>
              <div className="statBlock"><div className="small">Total</div><div className="n" id="statTotal">{stats.total}</div></div>
              <div className="statBlock"><div className="small">Corretas</div><div className="n" id="statCorrect">{stats.correct}</div></div>
              <div className="statBlock"><div className="small">Streak</div><div className="n" id="statStreak">{stats.streak}</div></div>
            </div>
          </div>
          <div className="small muted">Atalhos: Enter = enviar | Shift+Enter = nova linha</div>
        </section>

        <aside className="card panel">
          <h3>Sessões anteriores</h3>
          <div className="small">Clique em uma sessão para ver detalhes</div>
          <div className="history-list" style={{ marginTop: 12 }}>
            {storage.getPracticeSessions().length === 0 ? (
              <div className="small">Nenhuma sessão salva.</div>
            ) : (
              storage.getPracticeSessions().slice().reverse().slice(0, 6).map((s: any, idx: number) => (
                <div key={idx} className="history-item" tabIndex={0} onClick={() => { setSelectedSession(s); setShowSessionDetail(true); }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{new Date(s.timestamp).toLocaleString()}</div>
                    <div className="small">{s.total} perguntas • {s.correct} corretas</div>
                  </div>
                  <div className="small muted">Ver</div>
                </div>
              ))
            )}
          </div>
        </aside>
      </main>

      {showVideoModal && (
        <div className="modal show" onClick={(e) => { if (e.target === e.currentTarget) setShowVideoModal(false); }}>
          <div className="sheet panel" role="dialog" aria-modal="true">
            <h3>Escolher vídeos</h3>
            <div className="small">Marque os vídeos que deseja usar como fonte.</div>
            <div style={{ marginTop: 10 }}>
              {availableVideos.slice(0, 50).map((v) => (
                <label key={v.video_id} style={{ display: 'block', marginTop: 6 }}>
                  <input type="checkbox" checked={selectedVideos.includes(v.video_id)} onChange={(e) => {
                    if (e.target.checked) setSelectedVideos(prev => [...prev, v.video_id]);
                    else setSelectedVideos(prev => prev.filter(id => id !== v.video_id));
                  }} /> {v.title} <span className="small">({v.language || v.lang || 'en'})</span>
                </label>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
              <button className="btn ghost" onClick={() => setShowVideoModal(false)}>Cancelar</button>
              <button className="btn" onClick={() => { setShowVideoModal(false); alert('Vídeos salvos (exemplo)'); }}>Salvar</button>
            </div>
          </div>
        </div>
      )}

      {showSessionDetail && selectedSession && (
        <div className="modal show" onClick={(e) => { if (e.target === e.currentTarget) setShowSessionDetail(false); }}>
          <div className="sheet panel" role="dialog" aria-modal="true">
            <h3>Detalhes da sessão</h3>
            <div className="small" style={{ marginTop: 8 }}>
              <div><strong>Data:</strong> {new Date(selectedSession.timestamp).toLocaleString()}</div>
              <div><strong>Total:</strong> {selectedSession.total}</div>
              <div><strong>Corretas:</strong> {selectedSession.correct}</div>
              <div><strong>Erros:</strong> {selectedSession.incorrect}</div>
              <div style={{ marginTop: 8 }} className="small"><strong>Notas:</strong> {selectedSession.notes || '-'}</div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
              <button className="btn ghost" onClick={() => setShowSessionDetail(false)}>Fechar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

