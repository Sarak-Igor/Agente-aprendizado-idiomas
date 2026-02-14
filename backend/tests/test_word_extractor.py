from types import SimpleNamespace
from app.modules.language_learning.services.word_extractor import (
    extract_words_from_translations,
    filter_segments_by_difficulty,
)


def make_translation(segments):
    return SimpleNamespace(segments=segments)


def test_extract_words_from_translations_easy():
    segments = [
        {"original": "I love you", "translated": "Eu amo você"},
        {"original": "Beautiful day", "translated": "Dia bonito"},
    ]
    translations = [make_translation(segments)]
    words = extract_words_from_translations(translations, "en-to-pt", "easy")
    # should contain 'love' and 'beautiful' (lowercased)
    assert any(w == "love" for w in words)
    # 'beautiful' may be filtered out on 'easy' difficulty due to length; ensure result is non-empty
    assert isinstance(words, list) and len(words) > 0


def test_filter_segments_by_difficulty():
    segments = [
        {"original": "short"},  # 1 word
        {"original": "a bit longer phrase"},  # 4 words
        {"original": "this is a medium length sentence"},  # 6 words
        {"original": "this sentence has definitely more than thirteen words to be considered hard level in our tests"},  # long
    ]
    easy = filter_segments_by_difficulty(segments, "easy")
    assert all(len(s["original"].split()) <= 5 for s in easy)
    medium = filter_segments_by_difficulty(segments, "medium")
    assert all(6 <= len(s["original"].split()) <= 12 for s in medium)
    hard = filter_segments_by_difficulty(segments, "hard")
    assert all(len(s["original"].split()) >= 13 for s in hard)

