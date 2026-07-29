import json
import logging

from ..exceptions import AIServiceError
from ..providers import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent:
    """Comportamento comune ai due agent: costruzione prompt, chiamata al
    provider con un singolo retry, parsing JSON e validazione dello schema
    atteso. Se dopo due tentativi la risposta non è valida, solleva
    AIServiceError — nessun fallback silenzioso (spec sezione 10)."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def _build_prompt(self, **kwargs) -> str:
        raise NotImplementedError

    def _validate(self, data) -> None:
        """Solleva ValueError se `data` non rispetta lo schema atteso."""
        raise NotImplementedError

    def _run(self, **kwargs):
        prompt = self._build_prompt(**kwargs)
        last_error = None
        for attempt in (1, 2):
            try:
                raw = self.provider.complete(prompt)
                data = json.loads(raw)
                self._validate(data)
                return data
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "%s: tentativo %s fallito: %s",
                    self.__class__.__name__, attempt, exc,
                )
        raise AIServiceError(
            f"{self.__class__.__name__} fallito dopo 2 tentativi: {last_error}"
        )
