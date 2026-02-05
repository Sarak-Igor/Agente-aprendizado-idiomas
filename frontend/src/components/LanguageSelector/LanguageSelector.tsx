import './LanguageSelector.css';
import {
  SUPPORTED_TRANSLATION_LANGUAGES,
} from '../../config/languages';

interface LanguageOption {
  code: string;
  name: string;
}

interface LanguageSelectorProps {
  sourceLanguage: string;
  targetLanguage: string;
  onSourceChange: (lang: string) => void;
  onTargetChange: (lang: string) => void;
  languages?: LanguageOption[];
}

export const LanguageSelector = ({
  sourceLanguage,
  targetLanguage,
  onSourceChange,
  onTargetChange,
  languages,
}: LanguageSelectorProps) => {
  const options = languages && languages.length > 0 ? languages : SUPPORTED_TRANSLATION_LANGUAGES;

  return (
    <div className="language-selector">
      <div className="language-group">
        <label className="language-label">Idioma Original:</label>
        <select
          value={sourceLanguage}
          onChange={(e) => onSourceChange(e.target.value)}
          className="language-select"
        >
          {options.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      <div className="language-arrow">→</div>

      <div className="language-group">
        <label className="language-label">Idioma de Tradução:</label>
        <select
          value={targetLanguage}
          onChange={(e) => onTargetChange(e.target.value)}
          className="language-select"
        >
          {options.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
