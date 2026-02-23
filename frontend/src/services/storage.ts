import { DEFAULT_SOURCE, DEFAULT_TARGET, isSupportedLanguage } from '../config/languages';

const STORAGE_KEYS = {
  GEMINI_API_KEY: 'gemini_api_key',
  SOURCE_LANGUAGE: 'source_language',
  TARGET_LANGUAGE: 'target_language',
  PRACTICE_STATS: 'practice_stats',
  PRACTICE_SESSIONS: 'practice_sessions',
  CURRENT_PHRASE: 'current_practice_phrase',
  CURRENT_USER_ANSWER: 'current_user_answer',
  AUTH_TOKEN: 'auth_token',
  USER_ID: 'user_id',
  USERNAME: 'username',
  REMEMBER_ME: 'remember_me',
  PRACTICE_OPTIONS: 'practice_options',
} as const;

export interface PracticeOptions {
  selectedModes: string[];
  direction: string;
  selectedDirections: string[];
  difficulty: string;
  selectedVideos: string[];
}

export const storage = {
  getGeminiApiKey: (): string | null => {
    return localStorage.getItem(STORAGE_KEYS.GEMINI_API_KEY);
  },

  setGeminiApiKey: (key: string): void => {
    localStorage.setItem(STORAGE_KEYS.GEMINI_API_KEY, key);
  },

  getSourceLanguage: (): string => {
    const stored = localStorage.getItem(STORAGE_KEYS.SOURCE_LANGUAGE) || DEFAULT_SOURCE;
    return isSupportedLanguage(stored) ? stored : DEFAULT_SOURCE;
  },

  setSourceLanguage: (lang: string): void => {
    if (isSupportedLanguage(lang)) {
      localStorage.setItem(STORAGE_KEYS.SOURCE_LANGUAGE, lang);
    } else {
      console.warn(`Idioma não suportado ao salvar sourceLanguage: ${lang}`);
    }
  },

  getTargetLanguage: (): string => {
    const stored = localStorage.getItem(STORAGE_KEYS.TARGET_LANGUAGE) || DEFAULT_TARGET;
    return isSupportedLanguage(stored) ? stored : DEFAULT_TARGET;
  },

  setTargetLanguage: (lang: string): void => {
    if (isSupportedLanguage(lang)) {
      localStorage.setItem(STORAGE_KEYS.TARGET_LANGUAGE, lang);
    } else {
      console.warn(`Idioma não suportado ao salvar targetLanguage: ${lang}`);
    }
  },

  getPracticeStats: (): { total: number; correct: number; incorrect: number; streak: number; skipped: number } | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PRACTICE_STATS);
      if (stored) {
        const stats = JSON.parse(stored);
        // Garante compatibilidade com versões antigas que não tinham skipped
        if (stats.skipped === undefined) {
          stats.skipped = 0;
        }
        return stats;
      }
    } catch (error) {
      console.error('Erro ao carregar estatísticas de prática:', error);
    }
    return null;
  },

  setPracticeStats: (stats: { total: number; correct: number; incorrect: number; streak: number; skipped: number }): void => {
    try {
      localStorage.setItem(STORAGE_KEYS.PRACTICE_STATS, JSON.stringify(stats));
    } catch (error) {
      console.error('Erro ao salvar estatísticas de prática:', error);
    }
  },

  clearPracticeStats: (): void => {
    localStorage.removeItem(STORAGE_KEYS.PRACTICE_STATS);
  },

  savePracticeSession: (session: { total: number; correct: number; incorrect: number; streak: number; skipped: number; timestamp: string }): void => {
    try {
      const sessions = storage.getPracticeSessions();
      sessions.push(session);
      // Mantém apenas as últimas 50 sessões
      const recentSessions = sessions.slice(-50);
      localStorage.setItem(STORAGE_KEYS.PRACTICE_SESSIONS, JSON.stringify(recentSessions));
    } catch (error) {
      console.error('Erro ao salvar sessão de prática:', error);
    }
  },

  getPracticeSessions: (): Array<{ total: number; correct: number; incorrect: number; streak: number; timestamp: string }> => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PRACTICE_SESSIONS);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (error) {
      console.error('Erro ao carregar sessões de prática:', error);
    }
    return [];
  },

  saveCurrentPhrase: (phrase: any, userAnswer: string): void => {
    try {
      if (phrase && !userAnswer.trim()) {
        // Só salva se não foi respondida
        localStorage.setItem(STORAGE_KEYS.CURRENT_PHRASE, JSON.stringify(phrase));
        localStorage.setItem(STORAGE_KEYS.CURRENT_USER_ANSWER, userAnswer);
      } else {
        // Limpa se foi respondida
        localStorage.removeItem(STORAGE_KEYS.CURRENT_PHRASE);
        localStorage.removeItem(STORAGE_KEYS.CURRENT_USER_ANSWER);
      }
    } catch (error) {
      console.error('Erro ao salvar frase atual:', error);
    }
  },

  getCurrentPhrase: (): { phrase: any; userAnswer: string } | null => {
    try {
      const phraseStr = localStorage.getItem(STORAGE_KEYS.CURRENT_PHRASE);
      const userAnswer = localStorage.getItem(STORAGE_KEYS.CURRENT_USER_ANSWER) || '';
      if (phraseStr) {
        return {
          phrase: JSON.parse(phraseStr),
          userAnswer: userAnswer
        };
      }
    } catch (error) {
      console.error('Erro ao carregar frase atual:', error);
    }
    return null;
  },

  clearCurrentPhrase: (): void => {
    localStorage.removeItem(STORAGE_KEYS.CURRENT_PHRASE);
    localStorage.removeItem(STORAGE_KEYS.CURRENT_USER_ANSWER);
  },

  getPracticeOptions: (): PracticeOptions | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PRACTICE_OPTIONS);
      if (stored) return JSON.parse(stored);
    } catch (error) {
      console.error('Erro ao carregar opções de prática:', error);
    }
    return null;
  },

  setPracticeOptions: (options: PracticeOptions): void => {
    try {
      localStorage.setItem(STORAGE_KEYS.PRACTICE_OPTIONS, JSON.stringify(options));
    } catch (error) {
      console.error('Erro ao salvar opções de prática:', error);
    }
  },

  // Autenticação
  getAuthToken: (): string | null => {
    // Tenta primeiro localStorage, depois sessionStorage
    return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || sessionStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  },

  setAuthToken: (token: string, rememberMe: boolean = true): void => {
    const storageType = rememberMe ? localStorage : sessionStorage;
    storageType.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    if (rememberMe) {
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, 'true');
    } else {
      localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
    }
  },

  clearAuthToken: (): void => {
    // Limpa ambos storages
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER_ID);
    localStorage.removeItem(STORAGE_KEYS.USERNAME);
    sessionStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    sessionStorage.removeItem(STORAGE_KEYS.USER_ID);
    sessionStorage.removeItem(STORAGE_KEYS.USERNAME);
    localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
  },

  setUserInfo: (userId: string, username: string, rememberMe: boolean = true): void => {
    const storageType = rememberMe ? localStorage : sessionStorage;
    storageType.setItem(STORAGE_KEYS.USER_ID, userId);
    storageType.setItem(STORAGE_KEYS.USERNAME, username);
  },

  getUserId: (): string | null => {
    return localStorage.getItem(STORAGE_KEYS.USER_ID) || sessionStorage.getItem(STORAGE_KEYS.USER_ID);
  },

  getUsername: (): string | null => {
    return localStorage.getItem(STORAGE_KEYS.USERNAME) || sessionStorage.getItem(STORAGE_KEYS.USERNAME);
  },

  getRememberMe: (): boolean => {
    const stored = localStorage.getItem(STORAGE_KEYS.REMEMBER_ME);
    return stored === 'true';
  },

  setRememberMe: (rememberMe: boolean): void => {
    if (rememberMe) {
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, 'true');
    } else {
      localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
    }
  },
};
