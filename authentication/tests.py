from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.generics import ListAPIView
from rest_framework.test import APIRequestFactory

from categories.models import Category
from notions.models import Notion
from cards.models import Card
from .mixins import UserFilteredQuerysetMixin
from .permissions import IsOwner

User = get_user_model()


class IsOwnerPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user1 = User.objects.create_user(username='u1', password='pass12345!')
        self.user2 = User.objects.create_user(username='u2', password='pass12345!')
        self.category = Category.objects.create(user=self.user1, name='Bio')
        self.notion = Notion.objects.create(user=self.user1, category=self.category, raw_content='x')
        self.card = Card.objects.create(notion=self.notion, card_type=Card.CardType.ATOMIC_QA, question='Q?')

    def _request_for(self, user):
        request = self.factory.get('/fake/')
        request.user = user
        return request

    def test_owner_direct_field_allowed(self):
        class FakeView:
            owner_path = 'user'
        perm = IsOwner()
        self.assertTrue(perm.has_object_permission(self._request_for(self.user1), FakeView(), self.category))

    def test_owner_direct_field_denied(self):
        class FakeView:
            owner_path = 'user'
        perm = IsOwner()
        self.assertFalse(perm.has_object_permission(self._request_for(self.user2), FakeView(), self.category))

    def test_owner_nested_field_allowed(self):
        class FakeView:
            owner_path = 'notion.user'
        perm = IsOwner()
        self.assertTrue(perm.has_object_permission(self._request_for(self.user1), FakeView(), self.card))

    def test_owner_nested_field_denied(self):
        class FakeView:
            owner_path = 'notion.user'
        perm = IsOwner()
        self.assertFalse(perm.has_object_permission(self._request_for(self.user2), FakeView(), self.card))


class UserFilteredQuerysetMixinTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user1 = User.objects.create_user(username='u1', password='pass12345!')
        self.user2 = User.objects.create_user(username='u2', password='pass12345!')
        Category.objects.create(user=self.user1, name='Bio')
        Category.objects.create(user=self.user2, name='Chimica')

    def test_queryset_filtered_by_owner(self):
        class FakeCategoryListView(UserFilteredQuerysetMixin, ListAPIView):
            queryset = Category.objects.all()
            owner_lookup = 'user'

        view = FakeCategoryListView()
        request = self.factory.get('/fake/')
        request.user = self.user1
        view.request = request

        qs = view.get_queryset()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().user, self.user1)
