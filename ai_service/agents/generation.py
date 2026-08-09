"""
Sostituisce interamente: remembro-backend/ai_service/agents/generation.py

Due modifiche (Fase 15, validazione qualità agenti):

1. GENERATION_PROMPT: il vincolo sui key_points era menzionato una volta
   di sfuggita. Ora è esplicito, ripetuto nel formato di risposta e con
   l'istruzione su cosa fare quando il contenuto ha più di 5 elementi
   (sceglierne 5, non elencarli tutti).

2. _normalize(): se il modello produce comunque più di 5 key_points,
   vengono troncati ai primi 5 con un warning nei log, invece di far
   fallire la generazione. Sul set di validazione questo caso causava un
   retry nel 15% delle nozioni e un fallimento totale nel 5% (contenuti
   con molti elementi elencabili, es. le cause della caduta dell'Impero
   romano). Perdere il sesto punto chiave è preferibile a mostrare
   "generazione fallita" dopo due chiamate a pagamento.

Il limite minimo di 2 key_points resta un errore vero (non è
recuperabile inventando dati), come il resto della validazione.
"""
import logging

from .base import BaseAgent

logger = logging.getLogger(__name__)

VALID_CARD_TYPES = {"atomic_qa", "atomic_cloze", "synthesis"}
MIN_KEY_POINTS = 2
MAX_KEY_POINTS = 5

GENERATION_PROMPT = """Sei un assistente che trasforma nozioni di studio in card di ripasso.

Ricevi un testo e devi:
1. Valutare se è un fatto atomico (una singola informazione, es. una data, un termine) o un concetto complesso che richiede più card.
2. Se atomico: genera 1 card di tipo "atomic_qa" o "atomic_cloze".
3. Se complesso: scomponilo in card "atomic_qa" (una per concetto chiave, max 6), più 1 card "synthesis" che chiede di spiegare l'insieme con parole proprie.
4. Per ogni card genera anche "key_points": gli elementi essenziali che una risposta corretta deve contenere (usati per valutare le risposte, non mostrati all'utente).

VINCOLO OBBLIGATORIO sui key_points: minimo 2, MASSIMO 5 per ogni card.
Se il contenuto avrebbe più di 5 elementi rilevanti, NON elencarli tutti:
scegli i 5 più importanti, oppure distribuisci gli altri su una card
separata. Una card con 6 o più key_points è una risposta non valida.

Rispondi SOLO con JSON valido in questo formato (key_points: da 2 a 5 elementi, mai di più):
{{"cards": [{{"type": "atomic_qa|atomic_cloze|synthesis", "question": "...", "key_points": ["...", "..."]}}]}}

Testo della nozione: {raw_content}
Categoria: {category_name}
"""


class GenerationAgent(BaseAgent):
    def generate(self, raw_content: str, category_name: str) -> list[dict]:
        data = self._run(raw_content=raw_content, category_name=category_name)
        return data["cards"]

    def _build_prompt(self, raw_content: str, category_name: str) -> str:
        return GENERATION_PROMPT.format(
            raw_content=raw_content, category_name=category_name
        )

    def _normalize(self, data) -> None:
        """Tronca i key_points in eccesso invece di far fallire la generazione."""
        if not isinstance(data, dict):
            return
        cards = data.get("cards")
        if not isinstance(cards, list):
            return
        for card in cards:
            if not isinstance(card, dict):
                continue
            kp = card.get("key_points")
            if isinstance(kp, list) and len(kp) > MAX_KEY_POINTS:
                logger.warning(
                    "GenerationAgent: key_points troncati da %s a %s (card: %.60s)",
                    len(kp), MAX_KEY_POINTS, card.get("question", ""),
                )
                card["key_points"] = kp[:MAX_KEY_POINTS]

    def _validate(self, data) -> None:
        if not isinstance(data, dict) or "cards" not in data:
            raise ValueError("Manca la chiave 'cards' nell'output")
        cards = data["cards"]
        if not isinstance(cards, list) or not (1 <= len(cards) <= 7):
            raise ValueError("'cards' deve essere una lista di 1-7 elementi")
        for card in cards:
            if card.get("type") not in VALID_CARD_TYPES:
                raise ValueError(f"card type non valido: {card.get('type')}")
            if not card.get("question"):
                raise ValueError("'question' mancante")
            kp = card.get("key_points")
            if not isinstance(kp, list) or not (MIN_KEY_POINTS <= len(kp) <= MAX_KEY_POINTS):
                raise ValueError(
                    f"'key_points' deve avere {MIN_KEY_POINTS}-{MAX_KEY_POINTS} elementi"
                )
