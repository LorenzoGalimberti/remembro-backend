"""
Sostituisce interamente: remembro-backend/notions/tasks.py

Aggiunta rispetto alla versione con attivazione automatica: dopo una
generazione riuscita, salva una riga in AIUsageLog (user preso da
notion.user, dato che qui non c'è una request diretta essendo un task
Celery asincrono).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ai_service.agents.generation import GenerationAgent
from ai_service.exceptions import AIServiceError
from ai_service.models import AIUsageLog
from ai_service.providers import get_default_provider
from cards.models import Card

from .models import Notion

logger = logging.getLogger(__name__)


@shared_task
def generate_cards_from_notion(notion_id: int) -> None:
    try:
        notion = Notion.objects.get(id=notion_id)
    except Notion.DoesNotExist:
        logger.error("generate_cards_from_notion: Notion %s non trovata", notion_id)
        return

    provider = get_default_provider()
    agent = GenerationAgent(provider)

    try:
        cards_data = agent.generate(
            raw_content=notion.raw_content,
            category_name=notion.category.name,
        )
    except AIServiceError as exc:
        logger.error("Generazione fallita per Notion %s: %s", notion_id, exc)
        notion.generation_status = Notion.GenerationStatus.FAILED
        notion.save(update_fields=["generation_status"])
        return

    if provider.last_usage:
        AIUsageLog.objects.create(
            user=notion.user,
            call_type=AIUsageLog.CallType.GENERATION,
            model=provider.last_usage["model"],
            prompt_tokens=provider.last_usage["prompt_tokens"],
            completion_tokens=provider.last_usage["completion_tokens"],
            reasoning_tokens=provider.last_usage["reasoning_tokens"],
            total_tokens=provider.last_usage["total_tokens"],
        )

    now = timezone.now()
    cards = []
    for card in cards_data:
        if card["type"] == Card.CardType.SYNTHESIS:
            cards.append(Card(
                notion=notion,
                card_type=card["type"],
                question=card["question"],
                key_points=card["key_points"],
                status=Card.Status.DORMANT,
            ))
        else:
            cards.append(Card(
                notion=notion,
                card_type=card["type"],
                question=card["question"],
                key_points=card["key_points"],
                status=Card.Status.ACTIVE,
                interval_index=1,
                next_review_at=now + timedelta(days=1),
            ))

    Card.objects.bulk_create(cards)

    notion.generation_status = Notion.GenerationStatus.DONE
    notion.save(update_fields=["generation_status"])