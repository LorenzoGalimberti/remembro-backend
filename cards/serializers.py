from rest_framework import serializers
from .models import Card


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ['id', 'notion', 'card_type', 'question', 'key_points', 'next_review_at', 'interval_index', 'status', 'created_at']
        read_only_fields = fields