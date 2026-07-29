from abc import ABC, abstractmethod

from decouple import config
from openai import OpenAI, OpenAIError

from .exceptions import AIServiceError


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Invia il prompt al modello e ritorna la risposta testuale grezza
        (ci si aspetta JSON, ma il parsing è responsabilità del chiamante)."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config("LLM_API_KEY"), timeout=30)
        self.model = config("LLM_MODEL", default="o4-mini")

    def complete(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                reasoning_effort="low",
            )
        except OpenAIError as exc:
            raise AIServiceError(f"Chiamata a {self.model} fallita: {exc}") from exc
        return response.choices[0].message.content


def get_default_provider() -> LLMProvider:
    provider_name = config("LLM_PROVIDER", default="openai")
    if provider_name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Provider LLM non supportato: {provider_name}")
