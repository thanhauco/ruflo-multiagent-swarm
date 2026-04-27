"""Multi-provider LLM routing with a deterministic fallback provider."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens: int = 0


class LLMProvider(Protocol):
    name: str
    model: str
    capabilities: set[str]

    async def complete(self, prompt: str) -> LLMResponse:
        ...


class MockProvider:
    name = "mock"
    model = "deterministic-mock"
    capabilities = {"reasoning", "coding", "security", "fast"}

    async def complete(self, prompt: str) -> LLMResponse:
        digest = " ".join(prompt.strip().split())[:240]
        text = (
            "MockLLM response. Use deterministic project scaffolding and keep "
            f"outputs coherent with this request: {digest}"
        )
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=len(text.split()))


class OpenAIProvider:
    name = "openai"
    capabilities = {"coding", "reasoning", "fast", "security"}

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str) -> LLMResponse:
        from openai import AsyncOpenAI  # type: ignore

        client = AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else len(text.split())
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=tokens)


class AzureOpenAIProvider:
    name = "azure-openai"
    capabilities = {"coding", "reasoning", "fast", "security"}

    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = deployment
        self.api_version = api_version

    async def complete(self, prompt: str) -> LLMResponse:
        from openai import AsyncAzureOpenAI  # type: ignore

        client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else len(text.split())
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=tokens)


class AnthropicProvider:
    name = "anthropic"
    capabilities = {"reasoning", "security", "coding"}

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str) -> LLMResponse:
        from anthropic import AsyncAnthropic  # type: ignore

        client = AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model=self.model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts: list[str] = []
        for block in message.content:
            if getattr(block, "type", "") == "text":
                text_parts.append(getattr(block, "text", ""))
        text = "\n".join(text_parts)
        tokens = getattr(getattr(message, "usage", None), "output_tokens", 0) or len(text.split())
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=tokens)


class GroqProvider:
    name = "groq"
    capabilities = {"fast", "coding", "reasoning"}

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
        text = payload["choices"][0]["message"]["content"]
        tokens = payload.get("usage", {}).get("total_tokens", len(text.split()))
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=tokens)


class OllamaProvider:
    name = "ollama"
    capabilities = {"fast", "coding", "reasoning"}

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, prompt: str) -> LLMResponse:
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=body)
            response.raise_for_status()
            payload = response.json()
        text = payload.get("response", "")
        tokens = int(payload.get("eval_count", len(text.split())))
        return LLMResponse(text=text, provider=self.name, model=self.model, tokens=tokens)


class LLMRouter:
    def __init__(self, providers: list[LLMProvider] | None = None) -> None:
        self.providers = providers or [MockProvider()]
        self.role_policy = {
            "planner": "reasoning",
            "architect": "reasoning",
            "backend": "coding",
            "frontend": "coding",
            "database": "coding",
            "reviewer": "reasoning",
            "security": "security",
            "deployment": "coding",
            "general": "fast",
        }

    @classmethod
    def from_env(cls) -> "LLMRouter":
        providers: list[LLMProvider] = []
        if os.getenv("OPENAI_API_KEY"):
            providers.append(OpenAIProvider(os.environ["OPENAI_API_KEY"], os.getenv("OPENAI_MODEL", "gpt-4o-mini")))
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append(AnthropicProvider(os.environ["ANTHROPIC_API_KEY"], os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")))
        if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
            providers.append(
                AzureOpenAIProvider(
                    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                    api_key=os.environ["AZURE_OPENAI_API_KEY"],
                    deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "deployment"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                )
            )
        if os.getenv("GROQ_API_KEY"):
            providers.append(GroqProvider(os.environ["GROQ_API_KEY"], os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")))
        if os.getenv("OLLAMA_BASE_URL"):
            providers.append(OllamaProvider(os.environ["OLLAMA_BASE_URL"], os.getenv("OLLAMA_MODEL", "llama3.1")))
        providers.append(MockProvider())
        return cls(providers)

    async def complete(self, *, role: str, prompt: str) -> LLMResponse:
        capability = self.role_policy.get(role, "fast")
        eligible = [provider for provider in self.providers if capability in provider.capabilities]
        fallback = [provider for provider in self.providers if capability not in provider.capabilities]
        for provider in [*eligible, *fallback]:
            try:
                return await provider.complete(prompt)
            except Exception:
                continue
        return await self.providers[-1].complete(prompt)


