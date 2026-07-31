from abc import ABC, abstractmethod

from decouple import config
from openai import OpenAI, OpenAIError

from .exceptions import AIServiceError


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, json_mode: bool = True) -> str:          # <-- aggiunto json_mode
        """Invia il prompt al modello e ritorna la risposta testuale grezza.

        Se json_mode è True (default, usato da GenerationAgent ed
        EvaluationAgent) il provider forza il modello a rispondere con
        un oggetto JSON valido. Se False, il modello risponde con
        testo libero (usato dalla chat, fase 11)."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config("LLM_API_KEY"), timeout=30)
        self.model = config("LLM_MODEL", default="o4-mini")

    def complete(self, prompt: str, json_mode: bool = True) -> str:          # <-- aggiunto json_mode
        kwargs = {                                                          # <-- prima era diretto nella chiamata
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning_effort": "low",
        }
        if json_mode:                                                       # <-- response_format solo se json_mode=True
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.completions.create(**kwargs)
        except OpenAIError as exc:
            raise AIServiceError(f"Chiamata a {self.model} fallita: {exc}") from exc
        return response.choices[0].message.content


def get_default_provider() -> LLMProvider:
    provider_name = config("LLM_PROVIDER", default="openai")
    if provider_name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Provider LLM non supportato: {provider_name}")