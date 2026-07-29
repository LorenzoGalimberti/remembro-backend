from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from authentication.models import NotificationSettings
from cards.models import Card
from categories.models import Category
from notions.models import Notion

from .tasks import send_due_review_notifications

User = get_user_model()

FIXED_NOW = datetime(2026, 7, 29, 9, 30, tzinfo=dt_timezone.utc)  # le 9:30 UTC


class SendDueReviewNotificationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.settings_obj = NotificationSettings.objects.create(
            user=self.user, timezone='UTC', preferred_time=time(9, 0),
            expo_push_token='ExponentPushToken[abc]',
        )
        self.category = Category.objects.create(user=self.user, name='Biologia')
        self.notion = Notion.objects.create(user=self.user, category=self.category, raw_content='x' * 20)

    def make_due_card(self, category=None):
        notion = self.notion
        if category is not None:
            notion = Notion.objects.create(user=self.user, category=category, raw_content='y' * 20)
        return Card.objects.create(
            notion=notion,
            card_type=Card.CardType.ATOMIC_QA,
            question='?',
            status=Card.Status.ACTIVE,
            next_review_at=FIXED_NOW - timedelta(hours=1),
        )

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_sends_notification_when_hour_matches_and_cards_due(self, mock_send, mock_now):
        self.make_due_card()

        send_due_review_notifications()

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertIn('Biologia', kwargs['body'])
        self.assertEqual(kwargs['token'], 'ExponentPushToken[abc]')

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_no_send_when_hour_does_not_match(self, mock_send, mock_now):
        self.settings_obj.preferred_time = time(20, 0)
        self.settings_obj.save()
        self.make_due_card()

        send_due_review_notifications()

        mock_send.assert_not_called()

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_no_send_when_no_due_cards(self, mock_send, mock_now):
        send_due_review_notifications()
        mock_send.assert_not_called()

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_aggregates_multiple_categories(self, mock_send, mock_now):
        other_category = Category.objects.create(user=self.user, name='Chimica')
        self.make_due_card()
        self.make_due_card(category=other_category)

        send_due_review_notifications()

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertIn('Biologia', kwargs['body'])
        self.assertIn('Chimica', kwargs['body'])

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_invalid_timezone_is_skipped_without_error(self, mock_send, mock_now):
        self.settings_obj.timezone = 'Not/AZone'
        self.settings_obj.save()
        self.make_due_card()

        send_due_review_notifications()

        mock_send.assert_not_called()

    @patch('push_notifications.tasks.timezone.now', return_value=FIXED_NOW)
    @patch('push_notifications.tasks.send_expo_push')
    def test_users_without_token_are_ignored(self, mock_send, mock_now):
        self.settings_obj.expo_push_token = ''
        self.settings_obj.save()
        self.make_due_card()

        send_due_review_notifications()

        mock_send.assert_not_called()
