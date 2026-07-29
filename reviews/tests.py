from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from ai_service.exceptions import AIServiceError
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

    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_submit_review_correct(self, mock_agent_cls, mock_provider):
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

    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_review_on_draft_card_rejected(self, mock_agent_cls, mock_provider):
        self.card.status = Card.Status.DRAFT
        self.card.save()

        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })

        self.assertEqual(response.status_code, 400)
        mock_agent_cls.return_value.evaluate.assert_not_called()

    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_review_on_other_users_card_forbidden(self, mock_agent_cls, mock_provider):
        self.client.force_authenticate(self.other_user)

        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })

        self.assertEqual(response.status_code, 403)

    @patch('reviews.views.get_default_provider', return_value=MagicMock())
    @patch('reviews.views.EvaluationAgent')
    def test_ai_service_error_returns_502(self, mock_agent_cls, mock_provider):
        mock_agent_cls.return_value.evaluate.side_effect = AIServiceError('boom')

        response = self.client.post('/api/reviews/', {
            'card': self.card.id, 'answer_text': 'risposta',
        })

        self.assertEqual(response.status_code, 502)
        self.card.refresh_from_db()
        self.assertEqual(self.card.interval_index, 1)
