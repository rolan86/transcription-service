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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


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

        # Check z.ai
        zai_config = config.get("zai", {})
        if zai_config.get("api_key") or os.getenv("ZAI_API_KEY"):
            available.append("zai")

        # Check Claude
        claude_config = config.get("claude", {})
        if claude_config.get("api_key") or os.getenv("ANTHROPIC_API_KEY"):
            available.append("claude")

        # Check Ollama (local server)
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

        return available

    @staticmethod
    def get_ollama_models() -> List[str]:
        """Get list of models available in Ollama."""
        provider = OllamaProvider()
        return provider.get_available_models()
