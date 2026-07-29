from datetime import timedelta

from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.mixins import UserFilteredQuerysetMixin
from authentication.permissions import IsOwner
from .models import Card
from .serializers import CardSerializer


class CardViewSet(
    UserFilteredQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    owner_lookup = 'notion__user'
    owner_path = 'notion.user'

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        card = self.get_object()
        if card.status != Card.Status.DRAFT:
            return Response({'detail': 'Solo una bozza può essere confermata.'}, status=status.HTTP_400_BAD_REQUEST)
        card.status = Card.Status.ACTIVE
        card.interval_index = 1
        card.next_review_at = timezone.now() + timedelta(days=1)
        card.save()
        return Response(CardSerializer(card).data)

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        card = self.get_object()
        if card.status != Card.Status.DRAFT:
            return Response({'detail': 'Solo una bozza può essere scartata.'}, status=status.HTTP_400_BAD_REQUEST)
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        card = self.get_object()
        notion = card.notion
        card.delete()
        notion.generation_status = notion.GenerationStatus.PENDING
        notion.save(update_fields=['generation_status'])
        # TODO Fase 5: agganciare qui il trigger reale della generazione
        # (generate_cards_from_notion(notion.id)) che ricreerà le card.
        return Response(
            {'detail': 'Card cancellata, rigenerazione da innescare in Fase 5.'},
            status=status.HTTP_202_ACCEPTED,
        )