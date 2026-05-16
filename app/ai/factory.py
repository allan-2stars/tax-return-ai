"""Return the configured AI provider. Read AI_PROVIDER from env. Never instantiate providers elsewhere."""
from app.ai.providers.base import AIProvider
from app.config import settings


def get_provider() -> AIProvider:
    provider = settings.ai_provider.lower()
    if provider == "anthropic":
        from app.ai.providers.anthropic import AnthropicProvider
        return AnthropicProvider()
    if provider == "openai":
        from app.ai.providers.openai import OpenAIProvider
        return OpenAIProvider()
    if provider == "mock":
        from app.ai.providers.mock import MockProvider
        return MockProvider()
    raise ValueError(f"Unknown AI_PROVIDER: {provider!r}")


def provider_config_warning() -> str | None:
    provider = settings.ai_provider.lower()
    if provider == "anthropic" and not settings.anthropic_api_key:
        return "AI classification is not configured. Set ANTHROPIC_API_KEY or use AI_PROVIDER=mock."
    if provider == "openai" and not settings.openai_api_key:
        return "AI classification is not configured. Set OPENAI_API_KEY or use AI_PROVIDER=mock."
    return None
