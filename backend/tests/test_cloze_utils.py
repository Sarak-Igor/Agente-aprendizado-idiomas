from app.modules.language_learning.api import cloze

def test_normalize_text():
    assert cloze.normalize_text(" Hello, World! ") == "hello world"
    assert cloze.normalize_text(None) == ""
    assert cloze.normalize_text("Café") == "café"

def test_similarity_score_exact():
    assert cloze.similarity_score("hello", "hello") == 1.0

def test_similarity_score_fuzzy():
    s = cloze.similarity_score("running", "runing")
    assert s >= 0.6

