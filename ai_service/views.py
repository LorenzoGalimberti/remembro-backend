"""
Sostituisce interamente: remembro-backend/ai_service/views.py
(oggi contiene solo lo stub generato da Django, `render` non serve).

Stesso pattern di NotionViewSet.create(): controllo rate limit prima
di chiamare l'AI (429 se superato), poi validazione input col
serializer, poi chiamata all'agente con gestione esplicita
dell'errore (502 se il provider fallisce dopo il retry — nessun
fallback silenzioso).
"""

from decouple import config
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import get_user_timezone

from .chat_agent import ChatAgent
from .exceptions import AIServiceError
from .providers import get_default_provider
from .rate_limit import RateLimitExceeded, check_and_increment
from .serializers import ChatRequestSerializer, ChatResponseSerializer


class ChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            check_and_increment(
                user_id=request.user.id,
                kind='chat',
                limit=config('RATE_LIMIT_CHAT_PER_DAY', default=30, cast=int),
                user_timezone=get_user_timezone(request.user),
            )
        except RateLimitExceeded as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        request_serializer = ChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        agent = ChatAgent(provider=get_default_provider())
        try:
            reply_text = agent.reply(request_serializer.validated_data['message'])
        except AIServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        response_serializer = ChatResponseSerializer({'reply': reply_text})
        return Response(response_serializer.data, status=status.HTTP_200_OK)