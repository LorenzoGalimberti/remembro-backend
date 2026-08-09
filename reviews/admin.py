"""
Sostituisce interamente: remembro-backend/reviews/admin.py

Aggiunta (Fase 14 — Metriche e analytics): pagina custom dentro l'admin
Django, raggiungibile su /admin/metrics/, con le 3 metriche del piano:
retention del ripasso, frequenza di cattura, retention D7/D30. Protetta
come tutto il resto dell'admin (solo staff/superuser), nessun endpoint
pubblico nuovo.

Serve anche il template templates/admin/metrics_dashboard.html — file
successivo, senza quello questa pagina darebbe errore se visitata ora.

Definizioni usate (nessuna è nella spec, sono scelte MVP):
- retention del ripasso: % di ReviewLog degli ultimi 30 giorni con
  reviewed_at <= due_at (esclude le righe pre-Fase 14 che hanno due_at
  vuoto).
- retention D7/D30: % di utenti iscritti almeno N giorni fa che hanno
  fatto almeno un'attività (ripasso o nozione salvata) entro N giorni
  dall'iscrizione. Calcolo in Python, loop per utente — non efficiente
  su tanti utenti, accettabile per l'MVP (stesso compromesso già preso
  per il job notifiche).
"""
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from notions.models import Notion

from .models import ReviewLog


def metrics_view(request):
    now = timezone.now()

    # 1. Retention del ripasso (ultimi 30 giorni)
    window_start = now - timedelta(days=30)
    recent_reviews = ReviewLog.objects.filter(
        reviewed_at__gte=window_start,
        due_at__isnull=False,
    )
    total_reviews_30d = recent_reviews.count()
    on_time_reviews_30d = recent_reviews.filter(reviewed_at__lte=F('due_at')).count()
    review_retention_pct = (
        round(on_time_reviews_30d / total_reviews_30d * 100, 1) if total_reviews_30d else None
    )

    # 2. Frequenza di cattura (questa settimana vs scorsa)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    notions_this_week = Notion.objects.filter(created_at__gte=week_start).count()
    notions_last_week = Notion.objects.filter(
        created_at__gte=prev_week_start, created_at__lt=week_start
    ).count()

    # 3. Retention D7 / D30
    User = get_user_model()

    def cohort_retention(days):
        cohort = User.objects.filter(date_joined__lte=now - timedelta(days=days))
        cohort_count = cohort.count()
        if not cohort_count:
            return None
        active_count = 0
        for u in cohort:
            window_end = u.date_joined + timedelta(days=days)
            has_activity = (
                ReviewLog.objects.filter(
                    user=u, reviewed_at__gte=u.date_joined, reviewed_at__lte=window_end
                ).exists()
                or Notion.objects.filter(
                    user=u, created_at__gte=u.date_joined, created_at__lte=window_end
                ).exists()
            )
            if has_activity:
                active_count += 1
        return round(active_count / cohort_count * 100, 1)

    context = {
        **admin.site.each_context(request),
        'title': 'Metriche Remembro',
        'total_reviews_30d': total_reviews_30d,
        'on_time_reviews_30d': on_time_reviews_30d,
        'review_retention_pct': review_retention_pct,
        'notions_this_week': notions_this_week,
        'notions_last_week': notions_last_week,
        'retention_d7': cohort_retention(7),
        'retention_d30': cohort_retention(30),
    }
    return render(request, 'admin/metrics_dashboard.html', context)


_original_get_urls = admin.site.get_urls


def _get_urls_with_metrics():
    custom_urls = [
        path('metrics/', admin.site.admin_view(metrics_view), name='metrics_dashboard'),
    ]
    return custom_urls + _original_get_urls()


admin.site.get_urls = _get_urls_with_metrics


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('card', 'user', 'verdict', 'reviewed_at', 'interval_before', 'interval_after', 'due_at')
    list_filter = ('verdict',)
