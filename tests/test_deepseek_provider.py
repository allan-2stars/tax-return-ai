from app.ai.factory import get_provider
import app.ai.factory as ai_factory


def test_get_provider_deepseek_uses_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr(ai_factory.settings, "ai_provider", "deepseek")
    monkeypatch.setattr(ai_factory.settings, "deepseek_api_key", "deepseek-test-key")
    monkeypatch.setattr(ai_factory.settings, "deepseek_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(ai_factory.settings, "ai_model", "deepseek-v4-pro")

    provider = get_provider()
    assert provider.__class__.__name__ == "OpenAIProvider"
    assert provider.provider_name == "deepseek"
    assert provider.api_key == "deepseek-test-key"
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.model == "deepseek-v4-pro"

