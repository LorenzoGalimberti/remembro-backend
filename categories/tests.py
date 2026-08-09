from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category

User = get_user_model()


class CategoryAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='pass12345!')
        self.user2 = User.objects.create_user(username='u2', password='pass12345!')
        self.category1 = Category.objects.create(user=self.user1, name='Bio')
        self.category2 = Category.objects.create(user=self.user2, name='Chimica')

    def test_list_only_own_categories(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in response.data]
        self.assertIn(self.category1.id, ids)
        self.assertNotIn(self.category2.id, ids)

    def test_create_category_assigns_current_user(self):
        self.client.force_authenticate(self.user1)
        response = self.client.post('/api/categories/', {'name': 'Nuova'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.get(id=response.data['id']).user, self.user1)

    def test_cannot_rename_other_users_category(self):
        self.client.force_authenticate(self.user1)
        response = self.client.patch(f'/api/categories/{self.category2.id}/', {'name': 'Hack'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_other_users_category(self):
        self.client.force_authenticate(self.user1)
        response = self.client.delete(f'/api/categories/{self.category2.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_denied(self):
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
