export const SUPPORTED_TRANSLATION_LANGUAGES = [
  { code: 'en', name: 'Inglês' },
  { code: 'pt', name: 'Português' },
];

export const DEFAULT_SOURCE = 'en';
export const DEFAULT_TARGET = 'pt';

export const SUPPORTED_PRACTICE_DIRECTIONS = ['en-to-pt', 'pt-to-en'] as const;

export function isSupportedLanguage(code: string | null | undefined): boolean {
  if (!code) return false;
  return SUPPORTED_TRANSLATION_LANGUAGES.some((l) => l.code === code);
}

export function isSupportedDirection(direction: string | null | undefined): boolean {
  if (!direction) return false;
  return (SUPPORTED_PRACTICE_DIRECTIONS as readonly string[]).includes(direction);
}

