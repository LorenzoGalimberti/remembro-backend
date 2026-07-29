import json
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from .agents.evaluation import EvaluationAgent
from .agents.generation import GenerationAgent
from .exceptions import AIServiceError


def make_provider(*responses):
    """Provider fittizio che restituisce in sequenza le stringhe passate
    (una per ogni chiamata a .complete)."""
    provider = MagicMock()
    provider.complete.side_effect = responses
    return provider


VALID_GENERATION_RESPONSE = json.dumps({
    "cards": [
        {
            "type": "atomic_qa",
            "question": "Che cos'è X?",
            "key_points": ["punto 1", "punto 2"],
        }
    ]
})

VALID_EVALUATION_RESPONSE = json.dumps({
    "verdict": "correct",
    "missing_points": [],
    "feedback": "Ottimo lavoro!",
})


class GenerationAgentTests(SimpleTestCase):
    def test_success_first_attempt(self):
        provider = make_provider(VALID_GENERATION_RESPONSE)
        agent = GenerationAgent(provider)

        cards = agent.generate(raw_content="testo", category_name="Categoria")

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["type"], "atomic_qa")
        self.assertEqual(provider.complete.call_count, 1)

    def test_retries_once_then_succeeds(self):
        provider = make_provider("non è json valido", VALID_GENERATION_RESPONSE)
        agent = GenerationAgent(provider)

        cards = agent.generate(raw_content="testo", category_name="Categoria")

        self.assertEqual(len(cards), 1)
        self.assertEqual(provider.complete.call_count, 2)

    def test_fails_after_two_invalid_attempts(self):
        provider = make_provider("non è json", "ancora non è json")
        agent = GenerationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.generate(raw_content="testo", category_name="Categoria")

        self.assertEqual(provider.complete.call_count, 2)

    def test_rejects_invalid_card_type(self):
        bad_response = json.dumps({
            "cards": [{"type": "tipo_inesistente", "question": "?", "key_points": ["a", "b"]}]
        })
        provider = make_provider(bad_response, bad_response)
        agent = GenerationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.generate(raw_content="testo", category_name="Categoria")

    def test_rejects_too_few_key_points(self):
        bad_response = json.dumps({
            "cards": [{"type": "atomic_qa", "question": "?", "key_points": ["solo uno"]}]
        })
        provider = make_provider(bad_response, bad_response)
        agent = GenerationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.generate(raw_content="testo", category_name="Categoria")


class EvaluationAgentTests(SimpleTestCase):
    def test_success_first_attempt(self):
        provider = make_provider(VALID_EVALUATION_RESPONSE)
        agent = EvaluationAgent(provider)

        result = agent.evaluate(
            question="Che cos'è X?",
            key_points=["punto 1", "punto 2"],
            user_answer="risposta utente",
        )

        self.assertEqual(result["verdict"], "correct")
        self.assertEqual(provider.complete.call_count, 1)

    def test_retries_once_then_succeeds(self):
        provider = make_provider("json rotto", VALID_EVALUATION_RESPONSE)
        agent = EvaluationAgent(provider)

        result = agent.evaluate(
            question="Che cos'è X?", key_points=["a", "b"], user_answer="risposta"
        )

        self.assertEqual(result["verdict"], "correct")
        self.assertEqual(provider.complete.call_count, 2)

    def test_fails_after_two_invalid_attempts(self):
        provider = make_provider("rotto", "ancora rotto")
        agent = EvaluationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.evaluate(question="?", key_points=["a", "b"], user_answer="x")

    def test_rejects_invalid_verdict(self):
        bad_response = json.dumps({
            "verdict": "boh", "missing_points": [], "feedback": "ok"
        })
        provider = make_provider(bad_response, bad_response)
        agent = EvaluationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.evaluate(question="?", key_points=["a", "b"], user_answer="x")

    def test_rejects_missing_feedback(self):
        bad_response = json.dumps({
            "verdict": "correct", "missing_points": [], "feedback": ""
        })
        provider = make_provider(bad_response, bad_response)
        agent = EvaluationAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.evaluate(question="?", key_points=["a", "b"], user_answer="x")
