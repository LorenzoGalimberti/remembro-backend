from django.conf import settings
from django.db import models

from categories.models import Category


class Notion(models.Model):
    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AI_CHAT = 'ai_chat', 'AI Chat'
        EXTERNAL = 'external', 'External'

    class GenerationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notions',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='notions',
    )
    raw_content = models.TextField()
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )
    generation_status = models.CharField(
        max_length=10,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        preview = self.raw_content[:50]
        return f'{preview}...' if len(self.raw_content) > 50 else preview