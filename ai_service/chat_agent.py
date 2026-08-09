"""
Nuovo file: remembro-backend/ai_service/chat_agent.py

A differenza di GenerationAgent ed EvaluationAgent, non eredita da
BaseAgent: quella classe fa parsing JSON e validazione schema, ma la
risposta della chat è testo libero da mostrare all'utente, non dati
strutturati. Riusa comunque lo stesso LLMProvider (con json_mode=False,
vedi patch a providers.py) e lo stesso pattern "un singolo retry,
nessun fallback silenzioso" del resto di ai_service.

Nessuno storico di conversazione: ogni messaggio è indipendente
(spec sezione 3, piano fase 11 punto 1 — "non serve storicizzare
conversazioni complesse per l'MVP").
"""

import logging

from .exceptions import AIServiceError
from .providers import LLMProvider

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = """Sei l'assistente di Remembro, un'app che aiuta le persone a
imparare e ricordare. Rispondi in modo chiaro, conciso e accurato alla
domanda dell'utente, come farebbe una fonte di studio affidabile.
Vai dritto al contenuto utile, senza introdurti o aggiungere disclaimer
superflui: l'utente potrebbe salvare la tua risposta come nozione da
ripassare in futuro.
"""


class ChatAgent:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def reply(self, user_message: str) -> str:
        prompt = f"{CHAT_SYSTEM_PROMPT}\n\nDomanda dell'utente: {user_message}"

        last_error = None
        for attempt in (1, 2):
            try:
                text = self.provider.complete(prompt, json_mode=False)
                if text and text.strip():
                    return text.strip()
                last_error = AIServiceError("Risposta vuota dal provider LLM")
            except Exception as exc:
                last_error = exc
            logger.warning("ChatAgent: tentativo %s fallito: %s", attempt, last_error)

        raise AIServiceError(f"ChatAgent fallito dopo 2 tentativi: {last_error}")
