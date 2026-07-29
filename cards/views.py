from datetime import timedelta

from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.mixins import UserFilteredQuerysetMixin
from authentication.permissions import IsOwner
from notions.tasks import generate_cards_from_notion

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
        if self.action == 'due':
            return qs
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        card = self.get_object()
        if card.status != Card.Status.DRAFT:
            return Response({'detail': 'Solo una bozza può essere confermata.'}, status=status.HTTP_400_BAD_REQUEST)

        if card.card_type == Card.CardType.SYNTHESIS:
            # La sintesi resta dormiente finché le atomiche collegate non maturano (spec 5.3)
            card.status = Card.Status.DORMANT
        else:
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
        notion.cards.all().delete()
        notion.generation_status = notion.GenerationStatus.PENDING
        notion.save(update_fields=['generation_status'])
        generate_cards_from_notion.delay(notion.id)
        return Response(
            {'detail': 'Rigenerazione avviata.'},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['get'])
    def due(self, request):
        qs = self.get_queryset().filter(
            status=Card.Status.ACTIVE,
            next_review_at__lte=timezone.now(),
        )
        category_id = request.query_params.get('category')
        if category_id:
            qs = qs.filter(notion__category_id=category_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
