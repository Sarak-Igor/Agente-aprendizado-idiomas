import { useRef, useState } from 'react';
import { videoApi } from '../services/api';

type Mode = 'music-context' | 'new-context' | 'cloze' | 'sentence-scramble';
type Direction = 'en-to-pt' | 'pt-to-en' | 'all';

interface OrchestratorItem {
  mode: Mode;
  direction: Direction;
  payload: any; // the phrase object returned by backend
}

export function usePracticeOrchestrator() {
  const combosRef = useRef<{ mode: Mode; direction: Direction }[]>([]);
  const comboIndexRef = useRef(0);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const buildCombos = (modes: Mode[], directions: Direction[]) => {
    const combos: { mode: Mode; direction: Direction }[] = [];
    for (const m of modes) {
      for (const d of directions) {
        combos.push({ mode: m, direction: d });
      }
    }
    combosRef.current = combos;
    comboIndexRef.current = 0;
  };

  const nextCombo = () => {
    if (!combosRef.current || combosRef.current.length === 0) return null;
    const combo = combosRef.current[comboIndexRef.current];
    comboIndexRef.current = (comboIndexRef.current + 1) % combosRef.current.length;
    return combo;
  };

  const fetchItemForCombo = async (combo: { mode: Mode; direction: Direction }, difficulty: string, video_ids?: string[], api_keys?: any, custom_prompt?: string, preferred_agent?: any) : Promise<OrchestratorItem> => {
    console.debug(`Orchestrator: fetching combo`, combo, { difficulty, video_ids });
    if (combo.mode === 'music-context') {
      const data = await videoApi.getMusicPhrase({
        direction: combo.direction,
        difficulty,
        video_ids: video_ids && video_ids.length > 0 ? video_ids : undefined,
      });
      console.debug('Orchestrator: fetched music-context item', { combo, data });
      return { mode: combo.mode, direction: combo.direction, payload: data };
    } else if (combo.mode === 'cloze') {
      // request a cloze exercise (use gaps default = 1)
      const data = await videoApi.getCloze({
        mode: 'music-context',
        direction: combo.direction,
        difficulty,
        gaps: 1,
        video_ids: video_ids && video_ids.length > 0 ? video_ids : undefined,
      });
      console.debug('Orchestrator: fetched cloze item', { combo, data });
      return { mode: combo.mode, direction: combo.direction, payload: data };
    } else if (combo.mode === 'sentence-scramble') {
      const data = await videoApi.getScramblePhrase({
        direction: combo.direction,
        difficulty,
        video_ids: video_ids && video_ids.length > 0 ? video_ids : undefined,
      });
      console.debug('Orchestrator: fetched sentence-scramble item', { combo, data });
      return { mode: combo.mode, direction: combo.direction, payload: data };
    } else {
      const data = await videoApi.generatePracticePhrase({
        direction: combo.direction,
        difficulty,
        video_ids: video_ids && video_ids.length > 0 ? video_ids : undefined,
        api_keys: api_keys,
        custom_prompt: custom_prompt,
        preferred_agent: preferred_agent,
      });
      console.debug('Orchestrator: fetched new-context item', { combo, data });
      return { mode: combo.mode, direction: combo.direction, payload: data };
    }
  };

  // Public API
  const start = (modes: Mode[], directions: Direction[], difficulty: string, video_ids?: string[], api_keys?: any, custom_prompt?: string, preferred_agent?: any) => {
    buildCombos(modes, directions);
    setIsRunning(true);
    // no auto prefetch here; caller will request next()
  };

  const stop = () => {
    setIsRunning(false);
  };

  const next = async (difficulty: string, video_ids?: string[], api_keys?: any, custom_prompt?: string, preferred_agent?: any): Promise<OrchestratorItem | null> => {
    // Try up to combos.length attempts to find a combo that returns a valid item.
    if (!combosRef.current || combosRef.current.length === 0) return null;
    const attempts = combosRef.current.length;
    setIsLoading(true);
    try {
      for (let i = 0; i < attempts; i++) {
        const combo = nextCombo();
        if (!combo) return null;
        try {
          const item = await fetchItemForCombo(combo, difficulty, video_ids, api_keys, custom_prompt, preferred_agent);
          return item;
        } catch (err) {
          // Log and continue to next combo; this combo might not have data (404) or failed transiently.
          console.warn(`Orchestrator: combo failed, skipping. combo=${JSON.stringify(combo)} error=${err}`);
          continue;
        }
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    start,
    stop,
    next,
    isRunning,
    isLoading,
  };
}

