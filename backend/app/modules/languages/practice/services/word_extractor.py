import re
from typing import List, Optional


def filter_segments_by_difficulty(segments: List[dict], difficulty: str) -> List[dict]:
    """Filtra segmentos por dificuldade baseado no tamanho"""
    if difficulty == "easy":
        return [s for s in segments if len(s.get('original', '').split()) <= 5]
    elif difficulty == "medium":
        return [s for s in segments if 6 <= len(s.get('original', '').split()) <= 12]
    else:  # hard
        return [s for s in segments if len(s.get('original', '').split()) >= 13]


def extract_words_from_translations(
    translations,
    direction: Optional[str],
    difficulty: str
) -> List[str]:
    """Extrai palavras únicas das traduções."""
    words = set()

    for translation in translations:
        for segment in translation.segments:
            texts = []
            if direction == "en-to-pt":
                texts = [segment.get('original', '')]
            elif direction == "pt-to-en":
                texts = [segment.get('translated', '')]
            else:
                texts = [segment.get('original', ''), segment.get('translated', '')]

            for text in texts:
                text = re.sub(r'♪+', '', text)
                text = re.sub(r'[^\w\s]', ' ', text)
                segment_words = [w.lower() for w in text.split() if len(w) > 2]
                words.update(segment_words)

    if difficulty == "easy":
        common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could', 'should', 'may', 'might', 'must', 'to', 'of', 'in', 'on', 'at', 'for', 'with', 'by', 'from', 'as', 'and', 'or', 'but', 'if', 'when', 'where', 'what', 'who', 'why', 'how', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
        words = [w for w in words if w in common_words or len(w) <= 4]
    elif difficulty == "hard":
        words = [w for w in words if len(w) >= 6]

    return list(words)[:100]

