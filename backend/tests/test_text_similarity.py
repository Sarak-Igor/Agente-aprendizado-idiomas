from app.modules.language_learning.utils.text_similarity import (
    normalize_text,
    normalize_semantic,
    check_answer_similarity,
)


def test_normalize_text():
    assert normalize_text(" Hello, WORLD!! ") == "hello world"


def test_normalize_semantic():
    # 'tu' is equivalent to canonical 'você' in constants
    assert normalize_semantic("tu") == "você"
    # preserves other words
    assert normalize_semantic("beautiful") == "beautiful"


def test_check_answer_similarity_exact():
    assert check_answer_similarity("Hello world!", "hello world")
    # punctuation and casing differences
    assert check_answer_similarity("It's OK.", "its ok")

