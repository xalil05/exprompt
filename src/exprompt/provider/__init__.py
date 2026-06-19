"""Abstraction provider LLM — OpenAI, DeepSeek, OpenRouter, Custom."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from openai import OpenAI
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """Configuration chargée depuis .env ou variables d'env."""

    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0


class BaseProvider(ABC):
    """Classe abstraite pour un provider LLM."""

    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    @abstractmethod
    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        ...


class OpenAIProvider(BaseProvider):
    """Provider OpenAI / DeepSeek / OpenRouter / tout API compatible."""

    def __init__(self, settings: LLMSettings) -> None:
        super().__init__(settings)
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            http_client=httpx.Client(timeout=httpx.Timeout(120.0)),
        )

    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        model = kwargs.get("model", self.settings.llm_model)
        temperature = kwargs.get("temperature", 0.3)
        max_tokens = kwargs.get("max_tokens", 4096)

        resp = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            provider=self.settings.llm_provider,
            tokens_input=resp.usage.prompt_tokens if resp.usage else 0,
            tokens_output=resp.usage.completion_tokens if resp.usage else 0,
        )


def get_provider(settings: LLMSettings | None = None) -> BaseProvider:
    """Factory — retourne le bon provider selon la config."""
    if settings is None:
        settings = LLMSettings()

    return OpenAIProvider(settings)
