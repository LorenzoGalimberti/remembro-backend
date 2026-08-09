"""
Sostituisce interamente: remembro-backend/ai_service/agents/evaluation.py

Modifica (Fase 15, validazione qualità agenti): il tuning precedente
aveva reso l'agente meno rigido sui key_points, ma è andato troppo in
là — sul set di validazione ha giudicato "correct" una risposta
generica e vuota ("per motivi di sicurezza e di prestazioni" a una
domanda sul perché TLS usa sia crittografia asimmetrica sia simmetrica).

Il criterio aggiunto distingue una risposta sintetica ma sostanziale
(che resta "correct") da una generica e non verificabile, che potrebbe
valere per qualunque domanda simile e non dimostra comprensione. Resta
invariato il principio di non pretendere ogni singolo key_point.
Nessun cambio di schema o validazione, solo testo del prompt.
"""
from .base import BaseAgent

VALID_VERDICTS = {"correct", "partial", "incorrect"}

EVALUATION_PROMPT = """Sei un valutatore di risposte di studio. Ricevi una domanda, i punti chiave attesi, e la risposta data dall'utente. Giudica se la risposta è corretta, parziale o sbagliata, confrontando il significato (non le parole esatte).

Criteri per il verdetto:
- "correct": l'utente ha colto il concetto centrale della domanda, anche se non ha menzionato esplicitamente ogni singolo punto chiave. Non penalizzare l'assenza di dettagli secondari se il senso generale è corretto. La risposta può essere breve, purché contenga almeno un elemento specifico e verificabile che dimostri comprensione.
- "partial": la comprensione del concetto centrale è incompleta, vaga o in parte sbagliata. Rientrano qui anche le risposte GENERICHE: quelle che nominano l'argomento o ne indicano l'esito senza spiegare nulla di specifico, e che potrebbero valere per qualunque altra domanda simile. Non usare "partial" solo perché mancano dettagli minori quando il nucleo della risposta è giusto e argomentato.
- "incorrect": la risposta è sbagliata, non pertinente alla domanda, oppure ammette di non ricordare senza fornire contenuto.

Test pratico prima di assegnare "correct": la risposta contiene almeno un'informazione che una persona che NON conosce l'argomento non avrebbe potuto scrivere? Se no, non è "correct".

I punti chiave servono soprattutto a compilare "missing_points" come feedback su cosa approfondire, non come una checklist rigida da soddisfare per intero per ottenere "correct".

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
