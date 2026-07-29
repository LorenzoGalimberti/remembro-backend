from rest_framework import viewsets, permissions
from authentication.mixins import UserFilteredQuerysetMixin
from authentication.permissions import IsOwner
from .models import Notion
from .serializers import NotionSerializer


class NotionViewSet(UserFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Notion.objects.all()
    serializer_class = NotionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    owner_lookup = 'user'
    owner_path = 'user'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        # TODO Fase 5: qui va agganciato il trigger asincrono
        # generate_cards_from_notion(notion.id) verso Celery.