"""
Sostituisce interamente: remembro-backend/reviews/tests.py

Fix: test_submit_review_correct usava un provider mockato con
last_usage lasciato come MagicMock "nudo" (non un dict reale). La view
fa `if provider.last_usage: AIUsageLog.objects.create(...)`, quindi
provava a salvare dei MagicMock come valori di campo — Django li scambia
per espressioni di query e l'insert fallisce con
"F() expressions can only be used to update, not to insert".
Ora last_usage è un dict con valori reali, così il test copre anche la
scrittura in AIUsageLog (prima non verificata da nessun test).
"""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from ai_service.exceptions import AIServiceError
from ai_service.models import AIUsageLog
from ai_service.rate_limit import RateLimitExceeded
from cards.models import Card
from categories.models import Category
from notions.models import Notion

from .models import ReviewLog

User = get_user_model()


class ReviewSubmitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.other_user = User.objects.create_user(username='u2', password='pw')
        self.client.force_authenticate(self.user)
        self.category = Category.objects.create(user=self.user, name='Cat')
        self.notion = Notion.objects.create(user=self.user, category=self.category, raw_content='testo')
        self.card = Card.objects.create(
            notion=self.notion, card_type=Card.CardType.ATOMIC_QA,
            question='?', key_points=['a', 'b'],
            status=Card.Status.ACTIVE, interval_index=1,
        )

    @patch('reviews.views.check_and_increment')
    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_submit_review_correct(self, mock_agent_cls, mock_provider, mock_rate_limit):
        mock_provider.return_value.last_usage = {
            'model': 'gpt-test',
            'prompt_tokens': 100,
            'completion_tokens': 20,
            'reasoning_tokens': None,
            'total_tokens': 120,
        }
        mock_agent_cls.return_value.evaluate.return_value = {
            'verdict': 'correct', 'missing_points': [], 'feedback': 'bravo',
        }
        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['verdict'], 'correct')
        self.card.refresh_from_db()
        self.assertEqual(self.card.interval_index, 2)
        self.assertEqual(ReviewLog.objects.count(), 1)
        mock_rate_limit.assert_called_once()
        self.assertEqual(AIUsageLog.objects.count(), 1)
        usage_log = AIUsageLog.objects.get()
        self.assertEqual(usage_log.total_tokens, 120)
        self.assertEqual(usage_log.call_type, AIUsageLog.CallType.EVALUATION)

    @patch('reviews.views.check_and_increment')
    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_review_on_draft_card_rejected(self, mock_agent_cls, mock_provider, mock_rate_limit):
        self.card.status = Card.Status.DRAFT
        self.card.save()
        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })
        self.assertEqual(response.status_code, 400)
        mock_agent_cls.return_value.evaluate.assert_not_called()

    @patch('reviews.views.check_and_increment')
    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_review_on_other_users_card_forbidden(self, mock_agent_cls, mock_provider, mock_rate_limit):
        self.client.force_authenticate(self.other_user)
        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })
        self.assertEqual(response.status_code, 403)

    @patch('reviews.views.check_and_increment')
    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_ai_service_error_returns_502(self, mock_agent_cls, mock_provider, mock_rate_limit):
        mock_agent_cls.return_value.evaluate.side_effect = AIServiceError('boom')
        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })
        self.assertEqual(response.status_code, 502)
        self.card.refresh_from_db()
        self.assertEqual(self.card.interval_index, 1)

    @patch('reviews.views.check_and_increment')
    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_rate_limit_exceeded_returns_429(self, mock_agent_cls, mock_provider, mock_rate_limit):
        mock_rate_limit.side_effect = RateLimitExceeded('evaluation', 50)
        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })
        self.assertEqual(response.status_code, 429)
        mock_agent_cls.return_value.evaluate.assert_not_called()
        self.card.refresh_from_db()
        self.assertEqual(self.card.interval_index, 1)
