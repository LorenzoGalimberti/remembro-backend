from datetime import timedelta

from django.utils import timezone

from .models import Card

INTERVALS_DAYS = {1: 1, 2: 3, 3: 7, 4: 21}
MAX_INTERVAL_INDEX = max(INTERVALS_DAYS)


def apply_verdict(card: Card, verdict: str) -> tuple[int, int]:
    """Aggiorna interval_index e next_review_at della card in base al
    verdetto. Ritorna (interval_before, interval_after).
    - correct: avanza di un livello (max 21 giorni)
    - partial: mantiene lo stesso livello
    - incorrect: resetta a livello 1
    """
    interval_before = card.interval_index

    if verdict == "correct":
        interval_after = min(interval_before + 1, MAX_INTERVAL_INDEX)
    elif verdict == "partial":
        interval_after = interval_before if interval_before >= 1 else 1
    else:  # incorrect
        interval_after = 1

    card.interval_index = interval_after
    card.next_review_at = timezone.now() + timedelta(days=INTERVALS_DAYS[interval_after])
    card.save(update_fields=["interval_index", "next_review_at"])

    return interval_before, interval_after


def activate_synthesis_if_ready(notion) -> None:
    """Se la card synthesis della notion è dormant e tutte le card atomiche
    collegate hanno maturato interval_index >= 2, la attiva (spec 5.3)."""
    synthesis = notion.cards.filter(
        card_type=Card.CardType.SYNTHESIS, status=Card.Status.DORMANT
    ).first()
    if synthesis is None:
        return

    atomics = list(
        notion.cards.filter(
            card_type__in=[Card.CardType.ATOMIC_QA, Card.CardType.ATOMIC_CLOZE]
        )
    )
    if not atomics:
        return

    all_ready = all(
        c.status == Card.Status.ACTIVE and c.interval_index >= 2 for c in atomics
    )
    if not all_ready:
        return

    synthesis.status = Card.Status.ACTIVE
    synthesis.interval_index = 1
    synthesis.next_review_at = timezone.now()
    synthesis.save(update_fields=["status", "interval_index", "next_review_at"])
