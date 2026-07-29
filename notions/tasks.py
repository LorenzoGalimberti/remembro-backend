import logging

from celery import shared_task

from ai_service.agents.generation import GenerationAgent
from ai_service.exceptions import AIServiceError
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

    Card.objects.bulk_create([
        Card(
            notion=notion,
            card_type=card["type"],
            question=card["question"],
            key_points=card["key_points"],
            status=Card.Status.DRAFT,
        )
        for card in cards_data
    ])

    notion.generation_status = Notion.GenerationStatus.DONE
    notion.save(update_fields=["generation_status"])
