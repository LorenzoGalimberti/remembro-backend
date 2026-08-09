"""
Sostituisce interamente: remembro-backend/ai_service/models.py
(oggi è solo lo stub vuoto generato da Django)

AIUsageLog: una riga per ogni chiamata AI riuscita (chat, generazione,
valutazione), con i conteggi token restituiti da OpenAI. Serve per
analisi di costo, non per logica applicativa — per questo user usa
SET_NULL invece di CASCADE come Notion/Card/ReviewLog: è un log di
sistema, ha senso conservarlo anche se l'utente viene cancellato.

Dopo aver salvato questo file serve la migrazione:
    python manage.py makemigrations ai_service
    python manage.py migrate
"""

from django.conf import settings
from django.db import models


class AIUsageLog(models.Model):
    class CallType(models.TextChoices):
        CHAT = 'chat', 'Chat'
        GENERATION = 'generation', 'Generation'
        EVALUATION = 'evaluation', 'Evaluation'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_usage_logs',
    )
    call_type = models.CharField(max_length=20, choices=CallType.choices)
    model = models.CharField(max_length=50)
    prompt_tokens = models.PositiveIntegerField()
    completion_tokens = models.PositiveIntegerField()
    reasoning_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.call_type} [{self.model}] {self.total_tokens} token — {self.created_at:%Y-%m-%d %H:%M}'
