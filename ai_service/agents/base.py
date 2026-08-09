"""
Sostituisce interamente: remembro-backend/ai_service/agents/base.py

Aggiunta (Fase 15, validazione qualità agenti): hook _normalize(),
chiamato dopo il parsing JSON e prima di _validate(). Di default non fa
nulla; i sotto-agenti possono usarlo per correggere scostamenti minori
e recuperabili dell'output del modello, invece di far fallire l'intera
generazione e bruciare un retry.

Motivazione: sul set di validazione, il 15% delle nozioni ha richiesto
un retry e il 5% è fallito del tutto perché il modello produceva più di
5 key_points su contenuti con molti elementi elencabili (es. le cause
multiple della caduta dell'Impero romano). Un troncamento tracciato nei
log è preferibile a un errore in faccia all'utente; resta invece
inalterato il principio "nessun fallback silenzioso" per i fallimenti
veri del provider o per output strutturalmente invalidi.
"""
import json
import logging

from ..exceptions import AIServiceError
from ..providers import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent:
    """Comportamento comune ai due agent: costruzione prompt, chiamata al
    provider con un singolo retry, parsing JSON, normalizzazione e
    validazione dello schema atteso. Se dopo due tentativi la risposta non
    è valida, solleva AIServiceError — nessun fallback silenzioso
    (spec sezione 10)."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def _build_prompt(self, **kwargs) -> str:
        raise NotImplementedError

    def _normalize(self, data) -> None:
        """Corregge in place scostamenti minori e recuperabili dell'output.

        Default: nessuna modifica. Va usato solo per aggiustamenti che non
        alterano la sostanza della risposta (es. troncare una lista che
        eccede il limite), mai per inventare dati mancanti.
        """
        return None

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
                self._normalize(data)
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
