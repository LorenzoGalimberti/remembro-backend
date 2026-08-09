from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ai_service.rate_limit import RateLimitExceeded
from categories.models import Category

from .models import Notion

User = get_user_model()


class NotionAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='pass12345!')
        self.user2 = User.objects.create_user(username='u2', password='pass12345!')
        self.category1 = Category.objects.create(user=self.user1, name='Bio')
        self.category2 = Category.objects.create(user=self.user2, name='Chimica')

    @patch('notions.views.generate_cards_from_notion')
    @patch('notions.views.check_and_increment')
    def test_create_notion_with_own_category(self, mock_rate_limit, mock_task):
        self.client.force_authenticate(self.user1)
        response = self.client.post('/api/notions/', {
            'category': self.category1.id,
            'raw_content': 'Testo abbastanza lungo per superare la validazione.',
            'source_type': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_rate_limit.assert_called_once()

    @patch('notions.views.generate_cards_from_notion')
    @patch('notions.views.check_and_increment')
    def test_cannot_create_notion_with_others_category(self, mock_rate_limit, mock_task):
        self.client.force_authenticate(self.user1)
        response = self.client.post('/api/notions/', {
            'category': self.category2.id,
            'raw_content': 'Testo abbastanza lungo per superare la validazione.',
            'source_type': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('notions.views.generate_cards_from_notion')
    @patch('notions.views.check_and_increment')
    def test_raw_content_too_short_rejected(self, mock_rate_limit, mock_task):
        self.client.force_authenticate(self.user1)
        response = self.client.post('/api/notions/', {
            'category': self.category1.id,
            'raw_content': 'corto',
            'source_type': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_own_notions(self):
        Notion.objects.create(
            user=self.user1, category=self.category1,
            raw_content='Testo lungo abbastanza per validare bene.',
        )
        Notion.objects.create(
            user=self.user2, category=self.category2,
            raw_content='Altro testo lungo abbastanza per validare.',
        )
        self.client.force_authenticate(self.user1)
        response = self.client.get('/api/notions/')
        self.assertEqual(len(response.data), 1)

    @patch('notions.views.generate_cards_from_notion')
    @patch('notions.views.check_and_increment')
    def test_rate_limit_exceeded_returns_429(self, mock_rate_limit, mock_task):
        mock_rate_limit.side_effect = RateLimitExceeded('generation', 20)
        self.client.force_authenticate(self.user1)
        response = self.client.post('/api/notions/', {
            'category': self.category1.id,
            'raw_content': 'Testo abbastanza lungo per superare la validazione.',
            'source_type': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        mock_task.delay.assert_not_called()
