from rest_framework import viewsets, permissions
from authentication.mixins import UserFilteredQuerysetMixin
from authentication.permissions import IsOwner
from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(UserFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    owner_lookup = 'user'
    owner_path = 'user'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
