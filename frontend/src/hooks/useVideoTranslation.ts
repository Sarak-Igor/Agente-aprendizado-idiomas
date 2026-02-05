import { useState } from 'react';
import { videoApi, SubtitlesResponse } from '../services/api';
import { isSupportedLanguage } from '../config/languages';

export const useVideoTranslation = () => {
  const [subtitles, setSubtitles] = useState<SubtitlesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSubtitles = async (
    video_id: string,
    source_language: string,
    target_language: string
  ) => {
    setLoading(true);
    setError(null);
    try {
      // Validação local: atualmente o sistema só suporta pares en <-> pt
      if (!isSupportedLanguage(source_language) || !isSupportedLanguage(target_language) || source_language === target_language) {
        setError('Apenas Inglês ↔ Português são suportados para legendas atualmente.');
        setSubtitles(null);
        setLoading(false);
        return;
      }
      const data = await videoApi.getSubtitles(video_id, source_language, target_language);
      setSubtitles(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar legendas');
      setSubtitles(null);
    } finally {
      setLoading(false);
    }
  };

  return { subtitles, loading, error, loadSubtitles };
};
