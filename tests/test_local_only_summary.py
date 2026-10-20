"""Privacy tests: summaries are local (Ollama) by default and never fall back to cloud."""

import asyncio
import copy
import sys
from pathlib import Path
from unittest import mock

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from config.settings import Settings  # noqa: E402
from src.web.services.ai_provider import (  # noqa: E402
    AIProviderFactory,
    CloudNotAllowedError,
    OllamaProvider,
    OllamaUnavailableError,
    is_local_url,
)


@pytest.fixture
def ai_config():
    return copy.deepcopy(Settings.DEFAULT_CONFIG["ai"])


def test_default_is_ollama_local_and_cloud_off(ai_config):
    assert ai_config["provider"] == "ollama"
    assert ai_config["allow_cloud"] is False
    assert is_local_url(ai_config["ollama"]["base_url"])


def test_default_resolves_to_ollama_local(ai_config):
    with mock.patch.object(OllamaProvider, "ensure_ready", return_value=None):
        provider, ptype, is_local = AIProviderFactory.resolve(ai_config)
    assert (ptype, is_local) == ("ollama", True)
    assert isinstance(provider, OllamaProvider)


@pytest.mark.parametrize("name", ["zai", "claude"])
def test_cloud_without_opt_in_is_refused(ai_config, name):
    ai_config[name]["api_key"] = "dummy"
    with mock.patch("httpx.Client") as client, mock.patch("httpx.AsyncClient") as aclient:
        with pytest.raises(CloudNotAllowedError):
            AIProviderFactory.resolve(ai_config, name)
        with pytest.raises(CloudNotAllowedError):
            AIProviderFactory.resolve({**ai_config, "provider": name})
    client.assert_not_called()
    aclient.assert_not_called()


def test_non_local_ollama_url_needs_opt_in(ai_config):
    ai_config["ollama"]["base_url"] = "https://example.com:11434"
    with pytest.raises(CloudNotAllowedError):
        AIProviderFactory.resolve(ai_config)


def test_cloud_works_only_with_explicit_opt_in(ai_config):
    ai_config["zai"]["api_key"] = "dummy"
    ai_config["allow_cloud"] = True
    provider, ptype, is_local = AIProviderFactory.resolve(ai_config, "zai")
    assert (ptype, is_local) == ("zai", False)


def test_cloud_key_present_does_not_change_default_or_listing(ai_config):
    ai_config["zai"]["api_key"] = "dummy"
    with mock.patch.object(OllamaProvider, "is_available", return_value=False):
        assert AIProviderFactory.get_available_providers(ai_config) == []


def test_ollama_down_gives_clear_error_and_only_local_calls(ai_config):
    ai_config["zai"]["api_key"] = "dummy"  # a key exists; it must still not be used
    urls = []

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **k):
            urls.append(url)
            raise httpx.ConnectError("refused")

    with mock.patch("httpx.Client", FakeClient):
        with pytest.raises(OllamaUnavailableError) as exc:
            AIProviderFactory.resolve(ai_config)
    msg = str(exc.value)
    assert "Ollama is not running at http://localhost:11434" in msg
    assert "ollama serve" in msg and "ollama pull llama3" in msg
    assert "transcript is saved" in msg
    assert urls and all(is_local_url(u) for u in urls)


def test_complete_with_ollama_down_raises_clear_error_no_cloud():
    posted = []

    class FakeAsync:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            posted.append(url)
            raise httpx.ConnectError("refused")

    with mock.patch("httpx.AsyncClient", FakeAsync):
        with pytest.raises(OllamaUnavailableError):
            asyncio.run(OllamaProvider().complete("hi"))
    assert posted and all(is_local_url(u) for u in posted)


def test_missing_model_message():
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "mistral:latest"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **k):
            return FakeResp()

    with mock.patch("httpx.Client", FakeClient):
        with pytest.raises(OllamaUnavailableError) as exc:
            OllamaProvider(model="llama3").ensure_ready()
    assert "ollama pull llama3" in str(exc.value)


def test_env_opt_in_parsed_as_bool(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AI_ALLOW_CLOUD", "true")
    assert Settings().config["ai"]["allow_cloud"] is True
    monkeypatch.delenv("AI_ALLOW_CLOUD")
    assert Settings().config["ai"]["allow_cloud"] is False
