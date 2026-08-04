"""
Sostituisce interamente: remembro-backend/ai_service/providers.py

Aggiunta rispetto alla versione precedente (quella col logging warning):
dopo ogni chiamata riuscita, self.last_usage viene popolato con un
dizionario {model, prompt_tokens, completion_tokens, reasoning_tokens,
total_tokens}. Le view che chiamano gli agenti lo leggono subito dopo
per salvare la riga in AIUsageLog. Se una chiamata fallisce (eccezione),
last_usage non viene aggiornato — resta quello della chiamata riuscita
precedente o None se non c'è mai stata una chiamata riuscita.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from decouple import config
from openai import OpenAI, OpenAIError

from .exceptions import AIServiceError

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    #: dizionario con l'usage dell'ultima chiamata riuscita, o None.
    #: Non è parte stretta del contratto astratto (non tutti i provider
    #: futuri avranno per forza questo dettaglio), ma OpenAIProvider lo
    #: implementa e le view di questo progetto lo usano.
    last_usage: Optional[dict] = None

    @abstractmethod
    def complete(self, prompt: str, json_mode: bool = True) -> str:
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
        self.last_usage: Optional[dict] = None

    def complete(self, prompt: str, json_mode: bool = True) -> str:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning_effort": "low",
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.completions.create(**kwargs)
        except OpenAIError as exc:
            raise AIServiceError(f"Chiamata a {self.model} fallita: {exc}") from exc

        usage = response.usage
        if usage is not None:
            details = getattr(usage, "completion_tokens_details", None)
            reasoning_tokens = getattr(details, "reasoning_tokens", None)

            self.last_usage = {
                "model": self.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": usage.total_tokens,
            }

            # warning invece di info: il progetto non ha una LOGGING config
            # che stampi INFO in console (solo WARNING+), come dimostrano i
            # log "tentativo N fallito" dei retry che già vedi comparire.
            # Solo debug locale, non è un vero avviso applicativo.
            logger.warning(
                "OpenAI usage [%s]: prompt=%s completion=%s reasoning=%s total=%s",
                self.model,
                usage.prompt_tokens,
                usage.completion_tokens,
                reasoning_tokens,
                usage.total_tokens,
            )

        return response.choices[0].message.content


def get_default_provider() -> LLMProvider:
    provider_name = config("LLM_PROVIDER", default="openai")
    if provider_name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Provider LLM non supportato: {provider_name}")