from pydantic import ValidationError

from app.config import Settings
import app.ai.factory as ai_factory


def test_ai_provider_accepts_known_values():
    assert Settings(ai_provider="mock").ai_provider == "mock"
    assert Settings(ai_provider="openai").ai_provider == "openai"
    assert Settings(ai_provider="anthropic").ai_provider == "anthropic"
    assert Settings(ai_provider="deepseek").ai_provider == "deepseek"


def test_ai_provider_rejects_unknown_value():
    try:
        Settings(ai_provider="invalid-provider")
        assert False, "Expected invalid AI provider to raise validation error"
    except ValidationError as exc:
        assert "AI classification is not configured correctly" in str(exc)


def test_deepseek_config_warning_when_key_missing(monkeypatch):
    monkeypatch.setattr(ai_factory.settings, "ai_provider", "deepseek")
    monkeypatch.setattr(ai_factory.settings, "deepseek_api_key", "")
    warning = ai_factory.provider_config_warning()
    assert warning is not None
    assert "DEEPSEEK_API_KEY" in warning


def test_deepseek_config_warning_clears_when_key_present(monkeypatch):
    monkeypatch.setattr(ai_factory.settings, "ai_provider", "deepseek")
    monkeypatch.setattr(ai_factory.settings, "deepseek_api_key", "test-key")
    warning = ai_factory.provider_config_warning()
    assert warning is None
