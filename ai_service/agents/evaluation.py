from .base import BaseAgent

VALID_VERDICTS = {"correct", "partial", "incorrect"}

EVALUATION_PROMPT = """Sei un valutatore di risposte di studio. Ricevi una domanda, i punti chiave attesi, e la risposta data dall'utente. Giudica se la risposta è corretta, parziale o sbagliata, confrontando il significato (non le parole esatte).

Rispondi SOLO con JSON:
{{"verdict": "correct|partial|incorrect", "missing_points": ["..."], "feedback": "una frase breve, tono incoraggiante"}}

Domanda: {question}
Punti chiave attesi: {key_points}
Risposta dell'utente: {user_answer}
"""


class EvaluationAgent(BaseAgent):
    def evaluate(self, question: str, key_points: list[str], user_answer: str) -> dict:
        return self._run(
            question=question, key_points=key_points, user_answer=user_answer
        )

    def _build_prompt(self, question: str, key_points: list[str], user_answer: str) -> str:
        return EVALUATION_PROMPT.format(
            question=question, key_points=key_points, user_answer=user_answer
        )

    def _validate(self, data) -> None:
        if not isinstance(data, dict):
            raise ValueError("Output non è un oggetto JSON")
        if data.get("verdict") not in VALID_VERDICTS:
            raise ValueError(f"verdict non valido: {data.get('verdict')}")
        if not isinstance(data.get("missing_points"), list):
            raise ValueError("'missing_points' deve essere una lista")
        if not data.get("feedback"):
            raise ValueError("'feedback' mancante")
