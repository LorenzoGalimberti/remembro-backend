"""
Sostituisce interamente: remembro-backend/notions/tasks.py

Fase 15/16 — ripristinato il flusso bozza+conferma previsto dalla spec
(Fase 5 e Fase 10 del piano): le card generate tornano a nascere
`draft` invece di `active`/`dormant` come nella versione precedente
("attivazione automatica"). L'attivazione ora avviene solo tramite
CardViewSet.confirm() (cards/views.py, già esistente e testato), che
per le card atomiche imposta interval_index=1 e next_review_at, e per
la sintesi imposta 'dormant' (resta in attesa finché le atomiche
collegate non completano un ciclo, gestito da cards/scheduling.py).

Motivo del ripristino: senza fase di bozza, un utente non aveva modo
di scartare una card generata male (es. input che non era una vera
nozione di studio) se non chiedendo un intervento manuale sul database.
"""
import logging

from celery import shared_task

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

    cards = [
        Card(
            notion=notion,
            card_type=card["type"],
            question=card["question"],
            key_points=card["key_points"],
            status=Card.Status.DRAFT,
        )
        for card in cards_data
    ]
    Card.objects.bulk_create(cards)

    notion.generation_status = Notion.GenerationStatus.DONE
    notion.save(update_fields=["generation_status"])
