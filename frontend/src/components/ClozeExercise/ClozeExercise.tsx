import React, { useState } from 'react';

interface ClozeProps {
  cloze: {
    id: string;
    masked: string;
    answers: string[];
    source_language?: string;
    target_language?: string;
    video_title?: string;
  };
  onCheck: (answers: string[]) => Promise<{ is_correct: boolean; details?: any }>;
}

export const ClozeExercise: React.FC<ClozeProps> = ({ cloze, onCheck }) => {
  const [inputs, setInputs] = useState<string[]>(cloze.answers.map(() => ''));
  const [result, setResult] = useState<{ is_correct: boolean; details?: any } | null>(null);
  const [showHint, setShowHint] = useState(false);

  const handleChange = (idx: number, value: string) => {
    setInputs((prev) => {
      const copy = [...prev];
      copy[idx] = value;
      return copy;
    });
  };

  const handleCheck = async () => {
    const res = await onCheck(inputs);
    setResult(res);
  };

  return (
    <div className="cloze-exercise">
      <div className="cloze-header">
        {cloze.video_title && <div className="cloze-source">Música: {cloze.video_title}</div>}
      </div>
      <div className="cloze-masked-inline" style={{ fontSize: '1.25rem', marginTop: '8px' }}>
        {(() => {
          const parts = cloze.masked.split('____');
          const elements: any[] = [];
          for (let i = 0; i < parts.length; i++) {
            elements.push(<span key={`p-${i}`}>{parts[i]}</span>);
            if (i < parts.length - 1) {
              const inputIdx = elements.filter(el => String(el.key).startsWith('in-')).length;
              elements.push(
                <input
                  key={`in-${inputIdx}`}
                  value={inputs[inputIdx] || ''}
                  onChange={(e) => handleChange(inputIdx, e.target.value)}
                  placeholder={`...`}
                  style={{ display: 'inline-block', minWidth: '80px', margin: '0 6px', padding: '6px', borderRadius: '6px' }}
                />
              );
            }
          }
          return elements;
        })()}
      </div>
      <div style={{ marginTop: '12px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <button onClick={handleCheck} className="check-btn">Verificar Cloze</button>
        <button onClick={() => setShowHint((s) => !s)} className="help-btn" style={{ background: '#6c5ce7', color: 'white', padding: '8px 12px', borderRadius: '8px' }}>
          {showHint ? 'Esconder Ajuda' : 'Ajuda'}
        </button>
      </div>
      {showHint && cloze.translated && (
        <div style={{ marginTop: '10px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
          <strong>Dica (tradução):</strong>
          <div style={{ marginTop: '6px' }}>
            {(() => {
              // mask answers in translated text so we don't reveal the exact words
              const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              let hint = cloze.translated;
              if (!hint) return null;
              (cloze.answers || []).forEach((ans, idx) => {
                if (!ans) return;
                try {
                  const re = new RegExp('\\b' + escapeRegExp(ans) + '\\b', 'gi');
                  hint = hint.replace(re, '____');
                } catch (_) {
                  // ignore regex errors
                }
              });
              return <span>{hint}</span>;
            })()}
          </div>
        </div>
      )}
      {result && (
        <div style={{ marginTop: '12px' }}>
          {result.is_correct ? <div className="correct">✅ Correto</div> : <div className="incorrect">❌ Incorreto</div>}
        </div>
      )}
    </div>
  );
};

export default ClozeExercise;

