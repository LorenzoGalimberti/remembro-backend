"""
Sostituisce interamente: remembro-backend/ai_service/views.py

Aggiunta: dopo una risposta chat riuscita, salva una riga in
AIUsageLog leggendo provider.last_usage. Per poterlo leggere, il
provider ora si crea come variabile a parte invece che inline dentro
ChatAgent(...).
"""

from decouple import config
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import get_user_timezone

from .chat_agent import ChatAgent
from .exceptions import AIServiceError
from .models import AIUsageLog
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

        provider = get_default_provider()
        agent = ChatAgent(provider=provider)
        try:
            reply_text = agent.reply(request_serializer.validated_data['message'])
        except AIServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if provider.last_usage:
            AIUsageLog.objects.create(
                user=request.user,
                call_type=AIUsageLog.CallType.CHAT,
                model=provider.last_usage['model'],
                prompt_tokens=provider.last_usage['prompt_tokens'],
                completion_tokens=provider.last_usage['completion_tokens'],
                reasoning_tokens=provider.last_usage['reasoning_tokens'],
                total_tokens=provider.last_usage['total_tokens'],
            )

        response_serializer = ChatResponseSerializer({'reply': reply_text})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
