from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categories.models import Category
from notions.models import Notion

from .models import Card
from .scheduling import activate_synthesis_if_ready, apply_verdict

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


class SchedulingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.category = Category.objects.create(user=self.user, name='Cat')
        self.notion = Notion.objects.create(
            user=self.user, category=self.category, raw_content='testo',
        )

    def make_card(self, card_type=Card.CardType.ATOMIC_QA, interval_index=1, status=Card.Status.ACTIVE):
        return Card.objects.create(
            notion=self.notion,
            card_type=card_type,
            question='?',
            key_points=['a', 'b'],
            interval_index=interval_index,
            status=status,
        )

    def test_correct_advances_interval(self):
        card = self.make_card(interval_index=1)
        before, after = apply_verdict(card, 'correct')
        self.assertEqual((before, after), (1, 2))
        card.refresh_from_db()
        self.assertEqual(card.interval_index, 2)
        self.assertGreater(card.next_review_at, timezone.now())

    def test_correct_caps_at_max_interval(self):
        card = self.make_card(interval_index=4)
        before, after = apply_verdict(card, 'correct')
        self.assertEqual((before, after), (4, 4))

    def test_partial_keeps_same_level(self):
        card = self.make_card(interval_index=2)
        before, after = apply_verdict(card, 'partial')
        self.assertEqual((before, after), (2, 2))

    def test_incorrect_resets_to_one(self):
        card = self.make_card(interval_index=3)
        before, after = apply_verdict(card, 'incorrect')
        self.assertEqual((before, after), (3, 1))

    def test_synthesis_activates_when_all_atomics_ready(self):
        self.make_card(interval_index=2, status=Card.Status.ACTIVE)
        self.make_card(interval_index=2, status=Card.Status.ACTIVE)
        synthesis = self.make_card(
            card_type=Card.CardType.SYNTHESIS, interval_index=0, status=Card.Status.DORMANT
        )

        activate_synthesis_if_ready(self.notion)

        synthesis.refresh_from_db()
        self.assertEqual(synthesis.status, Card.Status.ACTIVE)
        self.assertEqual(synthesis.interval_index, 1)
        self.assertIsNotNone(synthesis.next_review_at)

    def test_synthesis_stays_dormant_if_not_all_atomics_ready(self):
        self.make_card(interval_index=2, status=Card.Status.ACTIVE)
        self.make_card(interval_index=0, status=Card.Status.ACTIVE)
        synthesis = self.make_card(
            card_type=Card.CardType.SYNTHESIS, interval_index=0, status=Card.Status.DORMANT
        )

        activate_synthesis_if_ready(self.notion)

        synthesis.refresh_from_db()
        self.assertEqual(synthesis.status, Card.Status.DORMANT)

    def test_no_op_if_no_dormant_synthesis(self):
        self.make_card(interval_index=2, status=Card.Status.ACTIVE)
        activate_synthesis_if_ready(self.notion)
