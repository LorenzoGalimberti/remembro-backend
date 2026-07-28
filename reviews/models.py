from django.conf import settings
from django.db import models

from cards.models import Card


class ReviewLog(models.Model):
    class Verdict(models.TextChoices):
        CORRECT = 'correct', 'Correct'
        PARTIAL = 'partial', 'Partial'
        INCORRECT = 'incorrect', 'Incorrect'

    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='review_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_logs',
    )
    answer_text = models.TextField()
    verdict = models.CharField(
        max_length=10,
        choices=Verdict.choices,
    )
    feedback_text = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    interval_before = models.PositiveSmallIntegerField()
    interval_after = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f'{self.card} — {self.verdict} ({self.reviewed_at:%Y-%m-%d})'