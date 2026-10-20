"""
Multi-provider LLM abstraction for AI features.
Supports z.ai (OpenAI-compatible), Claude API, Ollama, and local Llama models.
"""

import os
import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor


CLOUD_PROVIDERS = ("zai", "claude")
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class ProviderError(Exception):
    """Base error for provider selection problems. Message is user-facing."""


class CloudNotAllowedError(ProviderError):
    """A cloud provider was requested without explicit opt-in."""


class OllamaUnavailableError(ProviderError):
    """Local Ollama is not running or the model is missing."""


def is_local_url(url: Optional[str]) -> bool:
    """True only for http(s) URLs whose host is localhost, 127.0.0.1 or ::1."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url or "").hostname
    except ValueError:
        return False
    return host in LOCAL_HOSTS


def cloud_allowed(config: Optional[Dict[str, Any]]) -> bool:
    """Cloud providers need an explicit allow_cloud: true in the ai config."""
    value = (config or {}).get("allow_cloud", False)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return value is True


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate a completion from the model.

        Args:
            prompt: The user prompt
            system: Optional system prompt

        Returns:
            The generated text response
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is properly configured and available."""
        pass


class ZAIProvider(AIProvider):
    """z.ai API provider (OpenAI-compatible endpoint using Zhipu GLM models)."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.z.ai/api/paas/v4/", model: str = "glm-4.5"):
        self.api_key = api_key or os.getenv("ZAI_API_KEY")
        self.base_url = base_url or os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
        self.model = model or os.getenv("ZAI_MODEL", "glm-4.5")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise ImportError("openai package required for z.ai provider. Install with: pip install openai")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content


class ClaudeProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required for Claude provider. Install with: pip install anthropic")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or "",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class LlamaProvider(AIProvider):
    """Local Llama model provider via llama-cpp-python."""

    _executor = ThreadPoolExecutor(max_workers=1)

    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 4096):
        self.model_path = model_path or os.getenv("LLAMA_MODEL_PATH")
        self.n_ctx = n_ctx
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            if not self.model_path:
                raise ValueError("Model path required for Llama provider")
            try:
                from llama_cpp import Llama
                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    verbose=False
                )
            except ImportError:
                raise ImportError("llama-cpp-python package required for Llama provider. Install with: pip install llama-cpp-python")
        return self._llm

    def is_available(self) -> bool:
        if not self.model_path:
            return False
        return os.path.exists(self.model_path)

    def _generate_sync(self, full_prompt: str) -> str:
        result = self.llm(
            full_prompt,
            max_tokens=2048,
            stop=["</s>", "Human:", "User:"],
            echo=False
        )
        return result["choices"][0]["text"].strip()

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        # Format prompt for Llama
        if system:
            full_prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{prompt} [/INST]"
        else:
            full_prompt = f"<s>[INST] {prompt} [/INST]"

        # Run in thread pool since llama-cpp is synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self._generate_sync,
            full_prompt
        )
        return result


class OllamaProvider(AIProvider):
    """Ollama local model provider via REST API."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._available_models: Optional[List[str]] = None

    def is_available(self) -> bool:
        """Check if Ollama is running and has models available."""
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._available_models = models
                    return len(models) > 0
        except Exception:
            pass
        return False

    def ensure_ready(self) -> None:
        """Raise OllamaUnavailableError with a clear message if Ollama or the model is missing."""
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = [m.get("name", "") for m in response.json().get("models", [])]
        except Exception:
            raise OllamaUnavailableError(
                f"Ollama is not running at {self.base_url}. Start it with `ollama serve` "
                f"and pull the model with `ollama pull {self.model}`. "
                "Your transcript is saved; only the summary was skipped."
            )
        self._available_models = models
        wanted = self.model
        if not any(m == wanted or (":" not in wanted and m.split(":")[0] == wanted) for m in models):
            raise OllamaUnavailableError(
                f"Ollama is running at {self.base_url} but model '{self.model}' is not installed. "
                f"Pull it with `ollama pull {self.model}`. "
                "Your transcript is saved; only the summary was skipped."
            )

    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if self._available_models is None:
            self.is_available()
        return self._available_models or []

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise OllamaUnavailableError(
                f"Ollama is not running at {self.base_url}. Start it with `ollama serve` "
                f"and pull the model with `ollama pull {self.model}`. "
                "Your transcript is saved; only the summary was skipped."
            )


class AIProviderFactory:
    """Factory for creating AI providers."""

    @staticmethod
    def create(provider_type: str, config: Optional[Dict[str, Any]] = None) -> AIProvider:
        """
        Create an AI provider instance.

        Args:
            provider_type: One of 'zai', 'claude', 'ollama', or 'llama'
            config: Provider-specific configuration

        Returns:
            An AIProvider instance

        Raises:
            ValueError: If provider_type is unknown
        """
        config = config or {}

        if provider_type == "zai":
            return ZAIProvider(
                api_key=config.get("api_key"),
                base_url=config.get("base_url", "https://api.z.ai/api/paas/v4/"),
                model=config.get("model", "glm-4.5")
            )
        elif provider_type == "claude":
            return ClaudeProvider(
                api_key=config.get("api_key"),
                model=config.get("model", "claude-sonnet-4-20250514")
            )
        elif provider_type == "ollama":
            return OllamaProvider(
                model=config.get("model", "llama3"),
                base_url=config.get("base_url", "http://localhost:11434")
            )
        elif provider_type == "llama":
            return LlamaProvider(
                model_path=config.get("model_path"),
                n_ctx=config.get("n_ctx", 4096)
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def get_available_providers(config: Dict[str, Any]) -> list:
        """
        Get list of available (properly configured) providers.

        Args:
            config: AI configuration section from settings

        Returns:
            List of available provider names
        """
        available = []

        # Check Ollama (local server) first; local providers always lead the list
        # Cloud providers are listed only after explicit opt-in (allow_cloud).
        ollama_config = config.get("ollama", {})
        ollama_provider = OllamaProvider(
            model=ollama_config.get("model", "llama3"),
            base_url=ollama_config.get("base_url", "http://localhost:11434")
        )
        if ollama_provider.is_available():
            available.append("ollama")

        # Check Llama (local .gguf file)
        llama_config = config.get("llama", {})
        model_path = llama_config.get("model_path") or os.getenv("LLAMA_MODEL_PATH")
        if model_path and os.path.exists(model_path):
            available.append("llama")

        if cloud_allowed(config):
            zai_config = config.get("zai", {})
            if zai_config.get("api_key") or os.getenv("ZAI_API_KEY"):
                available.append("zai")
            claude_config = config.get("claude", {})
            if claude_config.get("api_key") or os.getenv("ANTHROPIC_API_KEY"):
                available.append("claude")

        return available

    @staticmethod
    def create_default(requested: Optional[str] = None) -> AIProvider:
        """Resolve a provider from saved settings (used by the MCP server). Same no-fallback rules."""
        from config.settings import Settings
        ai_config = Settings().config.get("ai", {})
        return AIProviderFactory.resolve(ai_config, requested)[0]

    @staticmethod
    def resolve(config: Optional[Dict[str, Any]], requested: Optional[str] = None):
        """
        Pick the provider for a request. No fallback, ever.

        Returns (provider, provider_type, is_local). Raises ProviderError
        subclasses with user-facing messages. Cloud providers (zai, claude, or
        any non-localhost endpoint) need ai.allow_cloud: true.
        """
        config = config or {}
        provider_type = requested or config.get("provider") or "ollama"
        provider_config = config.get(provider_type, {}) or {}

        if provider_type == "ollama":
            base_url = provider_config.get("base_url", DEFAULT_OLLAMA_URL)
            is_local = is_local_url(base_url)
        elif provider_type in CLOUD_PROVIDERS:
            is_local = False
        elif provider_type == "llama":
            is_local = True
        else:
            raise ProviderError(f"Unknown provider: {provider_type}")

        if not is_local and not cloud_allowed(config):
            raise CloudNotAllowedError(
                f"Provider '{provider_type}' sends your transcript to a cloud service and is disabled. "
                "Local Ollama is the default. To opt in, set ai.allow_cloud: true "
                "(or AI_ALLOW_CLOUD=true) and choose the provider explicitly."
            )

        provider = AIProviderFactory.create(provider_type, provider_config)
        if provider_type == "ollama":
            provider.ensure_ready()
        return provider, provider_type, is_local

    @staticmethod
    def get_ollama_models() -> List[str]:
        """Get list of models available in Ollama."""
        provider = OllamaProvider()
        return provider.get_available_models()
