from rest_framework import serializers
from .models import Notion


class NotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notion
        fields = ['id', 'category', 'raw_content', 'source_type', 'generation_status', 'created_at']
        read_only_fields = ['id', 'generation_status', 'created_at']

    def validate_raw_content(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Il testo deve contenere almeno 10 caratteri.')
        if len(value) > 5000:
            raise serializers.ValidationError('Il testo non può superare i 5000 caratteri.')
        return value

    def validate_category(self, value):
        request = self.context['request']
        if value.user != request.user:
            raise serializers.ValidationError('Categoria non valida.')
        return value
