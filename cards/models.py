from django.db import models

from notions.models import Notion


class Card(models.Model):
    class CardType(models.TextChoices):
        ATOMIC_QA = 'atomic_qa', 'Atomic Q&A'
        ATOMIC_CLOZE = 'atomic_cloze', 'Atomic Cloze'
        SYNTHESIS = 'synthesis', 'Synthesis'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        DORMANT = 'dormant', 'Dormant'

    notion = models.ForeignKey(
        Notion,
        on_delete=models.CASCADE,
        related_name='cards',
    )
    card_type = models.CharField(
        max_length=20,
        choices=CardType.choices,
    )
    question = models.TextField()
    key_points = models.JSONField(default=list)
    next_review_at = models.DateTimeField(null=True, blank=True)
    interval_index = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_review_at']

    def __str__(self):
        return f'[{self.card_type}] {self.question[:50]}'
