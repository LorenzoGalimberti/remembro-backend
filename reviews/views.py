from decouple import config
from rest_framework import mixins, permissions, viewsets
from rest_framework import status as http_status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ai_service.agents.evaluation import EvaluationAgent
from ai_service.exceptions import AIServiceError
from ai_service.providers import get_default_provider
from ai_service.rate_limit import RateLimitExceeded, check_and_increment
from authentication.mixins import UserFilteredQuerysetMixin
from authentication.models import get_user_timezone
from authentication.permissions import IsOwner
from cards.models import Card
from cards.scheduling import activate_synthesis_if_ready, apply_verdict

from .models import ReviewLog
from .serializers import ReviewLogSerializer, ReviewSubmitSerializer


class ReviewViewSet(
    UserFilteredQuerysetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ReviewLog.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    owner_lookup = 'user'
    owner_path = 'user'

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewSubmitSerializer
        return ReviewLogSerializer

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        card = input_serializer.validated_data['card']

        if card.notion.user_id != request.user.id:
            raise PermissionDenied('Card non accessibile.')
        if card.status != Card.Status.ACTIVE:
            raise ValidationError({'card': 'Solo le card attive possono essere ripassate.'})

        try:
            check_and_increment(
                user_id=request.user.id,
                kind='evaluation',
                limit=config('RATE_LIMIT_EVALUATIONS_PER_DAY', default=50, cast=int),
                user_timezone=get_user_timezone(request.user),
            )
        except RateLimitExceeded as exc:
            return Response({'detail': str(exc)}, status=http_status.HTTP_429_TOO_MANY_REQUESTS)

        answer_text = input_serializer.validated_data['answer_text']

        provider = get_default_provider()
        agent = EvaluationAgent(provider)
        try:
            result = agent.evaluate(
                question=card.question,
                key_points=card.key_points,
                user_answer=answer_text,
            )
        except AIServiceError as exc:
            return Response(
                {'detail': f'Valutazione non riuscita: {exc}'},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        interval_before, interval_after = apply_verdict(card, result['verdict'])

        review_log = ReviewLog.objects.create(
            card=card,
            user=request.user,
            answer_text=answer_text,
            verdict=result['verdict'],
            feedback_text=result.get('feedback', ''),
            interval_before=interval_before,
            interval_after=interval_after,
        )

        activate_synthesis_if_ready(card.notion)

        output = ReviewLogSerializer(review_log).data
        output['missing_points'] = result.get('missing_points', [])
        return Response(output, status=http_status.HTTP_201_CREATED)
