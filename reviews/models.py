"""
Sostituisce interamente: remembro-backend/reviews/models.py

Aggiunto il campo `due_at` a ReviewLog (Fase 14 — Metriche e analytics):
salva la scadenza prevista della card (Card.next_review_at PRIMA che la
view di submit la sovrascriva con il nuovo intervallo). Serve a calcolare
la retention del ripasso: reviewed_at <= due_at → ripasso "in finestra".
Nullable perché le righe già esistenti non hanno questo dato (e non è
recuperabile a posteriori).

Dopo aver salvato questo file serve la migrazione:
    python manage.py makemigrations reviews
    python manage.py migrate
"""
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
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f'{self.card} — {self.verdict} ({self.reviewed_at:%Y-%m-%d})'