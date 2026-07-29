from decouple import config
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from ai_service.rate_limit import RateLimitExceeded, check_and_increment
from authentication.mixins import UserFilteredQuerysetMixin
from authentication.models import get_user_timezone
from authentication.permissions import IsOwner

from .models import Notion
from .serializers import NotionSerializer
from .tasks import generate_cards_from_notion


class NotionViewSet(UserFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Notion.objects.all()
    serializer_class = NotionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    owner_lookup = 'user'
    owner_path = 'user'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def create(self, request, *args, **kwargs):
        try:
            check_and_increment(
                user_id=request.user.id,
                kind='generation',
                limit=config('RATE_LIMIT_GENERATIONS_PER_DAY', default=20, cast=int),
                user_timezone=get_user_timezone(request.user),
            )
        except RateLimitExceeded as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        notion = serializer.save(user=self.request.user)
        generate_cards_from_notion.delay(notion.id)
