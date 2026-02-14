import json
from types import SimpleNamespace
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app


def make_fake_segment(start=0.0, duration=1.0, original="Hello", translated="Olá"):
    return SimpleNamespace(start=start, duration=duration, original=original, translated=translated)


def test_video_process_flow(monkeypatch):
    client = TestClient(app)

    # Register a user
    register_payload = {
        "email": f"integ_test_user_{uuid4().hex}@example.com",
        "username": f"integuser_{uuid4().hex[:8]}",
        "native_language": "pt",
        "learning_language": "en"
    }
    r = client.post("/api/auth/register", json=register_payload)
    assert r.status_code == 201
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Patch YouTubeService methods
    def fake_extract_video_id(url):
        return "FAKE_VIDEO_ID"

    def fake_get_video_info(video_id):
        return {"title": "Fake Video", "duration": 123.0}

    def fake_get_transcript(video_id, langs):
        return [make_fake_segment(0.0, 2.0, "Hello world", "Olá mundo")]

    monkeypatch.setattr("app.modules.language_learning.services.youtube_service.YouTubeService.extract_video_id", staticmethod(fake_extract_video_id))
    monkeypatch.setattr("app.modules.language_learning.services.youtube_service.YouTubeService.get_video_info", staticmethod(fake_get_video_info))
    monkeypatch.setattr("app.modules.language_learning.services.youtube_service.YouTubeService.get_transcript", staticmethod(fake_get_transcript))

    # Patch TranslationServiceFactory.create to return a fake translator
    class FakeTranslator:
        def is_available(self):
            return True

        def translate_segments(self, segments, target_language, source_language, **kwargs):
            # convert segments to objects with attributes start,duration,original,translated
            return [make_fake_segment(s.start if hasattr(s, "start") else 0.0, getattr(s, "duration", 1.0), getattr(s, "text", "Hello"), "Olá")]

    monkeypatch.setattr("app.modules.language_learning.services.translation_factory.TranslationServiceFactory.create", staticmethod(lambda name, cfg: FakeTranslator()))

    # Call the process endpoint
    payload = {
        "youtube_url": "https://youtu.be/fake",
        "source_language": "en",
        "target_language": "pt",
        "gemini_api_key": None,
        "force_retranslate": False
    }

    resp = client.post("/api/video/process", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] in ("queued", "processing", "completed")

