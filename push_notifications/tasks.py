import logging
from collections import defaultdict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery import shared_task
from django.utils import timezone

from authentication.models import NotificationSettings
from cards.models import Card

from .services import send_expo_push

logger = logging.getLogger(__name__)


@shared_task
def send_due_review_notifications():
    now_utc = timezone.now()
    settings_qs = NotificationSettings.objects.exclude(expo_push_token="").select_related("user")

    for settings_obj in settings_qs:
        try:
            tz = ZoneInfo(settings_obj.timezone)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Timezone non valido per user %s: %s", settings_obj.user_id, settings_obj.timezone
            )
            continue

        local_now = now_utc.astimezone(tz)
        if local_now.hour != settings_obj.preferred_time.hour:
            continue

        due_cards = Card.objects.filter(
            notion__user=settings_obj.user,
            status=Card.Status.ACTIVE,
            next_review_at__lte=now_utc,
        ).select_related("notion__category")

        if not due_cards.exists():
            continue

        counts = defaultdict(int)
        for card in due_cards:
            counts[card.notion.category.name] += 1

        if len(counts) == 1:
            category_name, count = next(iter(counts.items()))
            body = f"Hai {count} nozioni di {category_name} da ripassare"
        else:
            total = sum(counts.values())
            parts = ", ".join(f"{n} di {cat}" for cat, n in counts.items())
            body = f"Hai {total} nozioni da ripassare ({parts})"

        send_expo_push(token=settings_obj.expo_push_token, title="Remembro", body=body)
