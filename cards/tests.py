from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from categories.models import Category
from notions.models import Notion
from .models import Card

User = get_user_model()


class CardAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='pass12345!')
        self.user2 = User.objects.create_user(username='u2', password='pass12345!')
        cat1 = Category.objects.create(user=self.user1, name='Bio')
        cat2 = Category.objects.create(user=self.user2, name='Chimica')
        self.notion1 = Notion.objects.create(user=self.user1, category=cat1, raw_content='x' * 20)
        self.notion2 = Notion.objects.create(user=self.user2, category=cat2, raw_content='y' * 20)
        self.card1 = Card.objects.create(notion=self.notion1, card_type=Card.CardType.ATOMIC_QA, question='Q1?')
        self.card2 = Card.objects.create(notion=self.notion2, card_type=Card.CardType.ATOMIC_QA, question='Q2?')

    def test_list_only_own_cards(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get('/api/cards/')
        ids = [c['id'] for c in response.data]
        self.assertIn(self.card1.id, ids)
        self.assertNotIn(self.card2.id, ids)

    def test_filter_by_status(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get('/api/cards/?status=draft')
        self.assertEqual(len(response.data), 1)

    def test_confirm_own_card(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(f'/api/cards/{self.card1.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card1.refresh_from_db()
        self.assertEqual(self.card1.status, Card.Status.ACTIVE)

    def test_cannot_confirm_others_card(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(f'/api/cards/{self.card2.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_discard_own_card(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post(f'/api/cards/{self.card1.id}/discard/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Card.objects.filter(id=self.card1.id).exists())