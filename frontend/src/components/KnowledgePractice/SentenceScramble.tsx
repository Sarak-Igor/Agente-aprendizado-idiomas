import React, { useEffect, useState } from 'react';
import { videoApi } from '../../services/api';

interface Props {
  direction: string;
  difficulty: string;
  video_ids?: string[] | undefined;
  onAnswered?: (correct: boolean) => void;
  onNext?: () => void;
  initialItem?: any | null;
}

const SentenceScramble: React.FC<Props> = ({ direction, difficulty, video_ids, onAnswered, onNext, initialItem }) => {
  const [item, setItem] = useState<any | null>(null);
  const [selectedTokens, setSelectedTokens] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ is_correct: boolean; correct_answer?: string } | null>(null);

  const load = async () => {
    setLoading(true);
    setItem(null);
    setSelectedTokens([]);
    setResult(null);
    try {
      const resp = await videoApi.getScramblePhrase({ direction, difficulty, video_ids });
      setItem(resp);
    } catch (err) {
      console.error('Erro ao carregar scramble', err);
      alert('Erro ao carregar exercício.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // React to changes in initialItem (parent orchestration) as well as direction/difficulty
    if (initialItem) {
      setItem(initialItem);
      setSelectedTokens([]);
      setResult(null);
    } else {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialItem, direction, difficulty]);

  const pickToken = (t: string) => {
    setSelectedTokens(prev => [...prev, t]);
  };

  const removeAt = (i: number) => {
    setSelectedTokens(prev => prev.filter((_, idx) => idx !== i));
  };

  const handleCheck = async () => {
    if (!item) return;
    try {
      const resp = await videoApi.checkScramble({ phrase_id: item.id, sequence: selectedTokens });
      setResult(resp);
      if (onAnswered) onAnswered(!!resp.is_correct);
    } catch (err) {
      console.error('Erro ao verificar scramble', err);
      alert('Erro ao verificar resposta.');
    }
  };

  return (
    <div className="sentence-scramble">
      {loading && <div>Carregando exercício...</div>}
      {!loading && item && (
        <div>
          <div style={{ marginBottom: '6px', color: 'var(--text-secondary)' }}>{item.video_title ? `Música: ${item.video_title}` : ''}</div>
          <div style={{ marginBottom: '8px' }}><strong>Ordene as palavras para formar a frase correta:</strong></div>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: '6px' }}>Palavras disponíveis:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {item.shuffled.map((t: string, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => pickToken(t)}
                    style={{
                      padding: '6px 12px',
                      minWidth: 36,
                      borderRadius: 8,
                      background: 'var(--btn-bg, #6c5ce7)',
                      color: 'var(--btn-text, #fff)',
                      border: 'none',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      fontSize: '0.9rem',
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: '6px' }}>Sua ordem:</div>
              <div style={{ minHeight: '56px', border: '1px dashed var(--border)', padding: '8px', borderRadius: '6px' }}>
                {selectedTokens.length === 0 && <div style={{ color: 'var(--text-secondary)' }}>Clique nas palavras para adicioná‑las na ordem desejada.</div>}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {selectedTokens.map((t, i) => (
                    <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <div style={{ padding: '6px 10px', borderRadius: 8, background: 'var(--chip-bg, #2d3436)', color: 'var(--chip-text, #fff)' }}>{t}</div>
                      <button onClick={() => removeAt(i)} className="skip-btn" style={{ padding: '4px 8px' }}>x</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {!result && (
            <div>
              <button onClick={handleCheck} className="check-btn" disabled={selectedTokens.length === 0}>Verificar</button>
              <button onClick={() => { setSelectedTokens([]); }} className="skip-btn" style={{ marginLeft: '8px' }}>Resetar</button>
              <button onClick={() => { load(); }} className="skip-btn" style={{ marginLeft: '8px' }}>Pular</button>
            </div>
          )}

          {result && (
            <div style={{ marginTop: '12px' }}>
              <div className={`answer-feedback ${result.is_correct ? 'correct' : 'incorrect'}`}>
                <div className="feedback-header">{result.is_correct ? '✅ Correto!' : '❌ Incorreto'}</div>
                {!result.is_correct && (
                  <div style={{ marginTop: '8px' }}>
                    <strong>Resposta correta:</strong>
                    <div style={{ fontStyle: 'italic', marginTop: '6px' }}>{result.correct_answer}</div>
                  </div>
                )}
              </div>

              {/* Tradução da frase (mostrada sempre após submissão) */}
              <div style={{ marginTop: '12px' }}>
                <div className="translation-card">
                  <div style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    <strong>Tradução:</strong>
                  </div>
                  <div style={{ fontStyle: 'italic' }}>
                    {item?.translated || '—'}
                  </div>
                  {item?.video_title && (
                    <div style={{ marginTop: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                      Música: {item.video_title}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginTop: '8px' }}>
                <button onClick={() => { if (onNext) onNext(); else load(); }} className="next-btn">Próxima</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SentenceScramble;

