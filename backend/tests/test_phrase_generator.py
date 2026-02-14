import types

from app.modules.language_learning.services import phrase_generator


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate_text(self, prompt, max_tokens=200):
        self.calls.append(prompt)
        if "Traduza o seguinte texto" in prompt or "Tradução:" in prompt:
            return "Eu amo seu belo coração"
        return "I love your beautiful heart"


def test_generate_phrase_with_llm(monkeypatch):
    fake = FakeLLM()
    # make randomness deterministic
    monkeypatch.setattr(phrase_generator.random, "randint", lambda *a, **k: 3)
    monkeypatch.setattr(phrase_generator.random, "sample", lambda lst, n: lst[:n])

    words = ["love", "heart", "beautiful", "sun"]
    result = phrase_generator.generate_phrase_with_llm(fake, words, "en", "pt", "medium")
    assert "phrase" in result
    assert result["phrase"]["original"] == "I love your beautiful heart"
    assert result["phrase"]["translated"] == "Eu amo seu belo coração"

