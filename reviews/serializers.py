from rest_framework import serializers

from cards.models import Card

from .models import ReviewLog


class ReviewSubmitSerializer(serializers.Serializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    answer_text = serializers.CharField(min_length=1, max_length=4000)


class ReviewLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewLog
        fields = [
            'id', 'card', 'answer_text', 'verdict', 'feedback_text',
            'reviewed_at', 'interval_before', 'interval_after',
        ]
        read_only_fields = fields
