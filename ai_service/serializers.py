"""
Nuovo file: remembro-backend/ai_service/serializers.py

Non c'è un modello dietro (la chat è stateless), quindi è un
serializers.Serializer semplice e non un ModelSerializer come
NotionSerializer. Stesso stile di validazione con messaggi in
italiano usato in notions/serializers.py.
"""

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(trim_whitespace=True)

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError('Scrivi un messaggio.')
        if len(value) > 2000:
            raise serializers.ValidationError('Il messaggio non può superare i 2000 caratteri.')
        return value


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()