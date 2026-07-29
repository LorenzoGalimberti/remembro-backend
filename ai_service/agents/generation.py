from .base import BaseAgent

VALID_CARD_TYPES = {"atomic_qa", "atomic_cloze", "synthesis"}

GENERATION_PROMPT = """Sei un assistente che trasforma nozioni di studio in card di ripasso.

Ricevi un testo e devi:
1. Valutare se è un fatto atomico (una singola informazione, es. una data, un termine) o un concetto complesso che richiede più card.
2. Se atomico: genera 1 card di tipo "atomic_qa" o "atomic_cloze".
3. Se complesso: scomponilo in card "atomic_qa" (una per concetto chiave, max 6), più 1 card "synthesis" che chiede di spiegare l'insieme con parole proprie.
4. Per ogni card genera anche "key_points": una lista di 2-5 elementi essenziali che una risposta corretta deve contenere (usata per valutare le risposte, non mostrata all'utente).

Rispondi SOLO con JSON valido in questo formato:
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
            if not isinstance(kp, list) or not (2 <= len(kp) <= 5):
                raise ValueError("'key_points' deve avere 2-5 elementi")
