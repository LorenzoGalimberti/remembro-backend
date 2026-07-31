"""
Sostituisce interamente: remembro-backend/ai_service/tests.py

Rispetto all'originale: aggiunto l'import di ChatAgent in cima, e
aggiunta la classe ChatAgentTests in fondo (dopo CheckAndIncrementTests).
Tutto il resto è identico a quello che avevi già.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .rate_limit import RateLimitExceeded, check_and_increment

from .agents.evaluation import EvaluationAgent
from .agents.generation import GenerationAgent
from .chat_agent import ChatAgent
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


class ChatAgentTests(SimpleTestCase):
    def test_success_first_attempt(self):
        provider = make_provider("La fotosintesi converte luce in energia chimica.")
        agent = ChatAgent(provider)

        reply = agent.reply("Cos'è la fotosintesi?")

        self.assertEqual(reply, "La fotosintesi converte luce in energia chimica.")
        self.assertEqual(provider.complete.call_count, 1)
        _, kwargs = provider.complete.call_args
        self.assertFalse(kwargs.get("json_mode", True))

    def test_retries_once_after_empty_reply_then_succeeds(self):
        provider = make_provider("   ", "Ecco la risposta vera.")
        agent = ChatAgent(provider)

        reply = agent.reply("Domanda")

        self.assertEqual(reply, "Ecco la risposta vera.")
        self.assertEqual(provider.complete.call_count, 2)

    def test_retries_once_after_exception_then_succeeds(self):
        provider = make_provider(RuntimeError("timeout"), "Risposta ok")
        agent = ChatAgent(provider)

        reply = agent.reply("Domanda")

        self.assertEqual(reply, "Risposta ok")
        self.assertEqual(provider.complete.call_count, 2)

    def test_fails_after_two_exceptions(self):
        provider = make_provider(RuntimeError("timeout"), RuntimeError("timeout"))
        agent = ChatAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.reply("Domanda")

        self.assertEqual(provider.complete.call_count, 2)

    def test_fails_after_two_empty_replies(self):
        provider = make_provider("   ", "")
        agent = ChatAgent(provider)

        with self.assertRaises(AIServiceError):
            agent.reply("Domanda")

        self.assertEqual(provider.complete.call_count, 2)


class _FakePipeline:
    def __init__(self, store):
        self.store = store
        self._ops = []

    def incr(self, key):
        self._ops.append(("incr", key))
        return self

    def expire(self, key, seconds):
        self._ops.append(("expire", key, seconds))
        return self

    def execute(self):
        for op in self._ops:
            if op[0] == "incr":
                self.store[op[1]] = self.store.get(op[1], 0) + 1
        self._ops = []


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        value = self.store.get(key)
        return str(value).encode() if value is not None else None

    def pipeline(self):
        return _FakePipeline(self.store)


class CheckAndIncrementTests(SimpleTestCase):
    def setUp(self):
        self.fake_redis = FakeRedis()
        patcher = patch("ai_service.rate_limit.get_redis_client", return_value=self.fake_redis)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_allows_up_to_limit_then_raises(self):
        check_and_increment(user_id=1, kind="generation", limit=2, user_timezone="UTC")
        check_and_increment(user_id=1, kind="generation", limit=2, user_timezone="UTC")
        with self.assertRaises(RateLimitExceeded):
            check_and_increment(user_id=1, kind="generation", limit=2, user_timezone="UTC")

    def test_different_users_have_independent_counters(self):
        check_and_increment(user_id=1, kind="generation", limit=1, user_timezone="UTC")
        # utente diverso, non deve essere influenzato dal contatore di user 1
        check_and_increment(user_id=2, kind="generation", limit=1, user_timezone="UTC")
        with self.assertRaises(RateLimitExceeded):
            check_and_increment(user_id=1, kind="generation", limit=1, user_timezone="UTC")

    def test_different_kinds_have_independent_counters(self):
        check_and_increment(user_id=1, kind="generation", limit=1, user_timezone="UTC")
        # 'evaluation' non deve risentire del contatore 'generation'
        check_and_increment(user_id=1, kind="evaluation", limit=1, user_timezone="UTC")
        with self.assertRaises(RateLimitExceeded):
            check_and_increment(user_id=1, kind="evaluation", limit=1, user_timezone="UTC")

    @patch("ai_service.rate_limit.config")
    def test_bypassed_when_rate_limit_disabled(self, mock_config):
        mock_config.return_value = False
        # anche con limit=0 non deve mai sollevare, il controllo è disattivato
        check_and_increment(user_id=1, kind="generation", limit=0, user_timezone="UTC")
        check_and_increment(user_id=1, kind="generation", limit=0, user_timezone="UTC")

    def test_invalid_timezone_falls_back_to_utc(self):
        # non deve sollevare ZoneInfoNotFoundError, deve usare UTC come fallback
        check_and_increment(user_id=1, kind="generation", limit=5, user_timezone="Not/AZone")