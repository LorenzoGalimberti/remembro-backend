import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import redis
from decouple import config

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(config("REDIS_URL"))
    return _redis_client


class RateLimitExceeded(Exception):
    def __init__(self, kind: str, limit: int):
        self.kind = kind
        self.limit = limit
        label = "generazioni" if kind == "generation" else "valutazioni"
        super().__init__(
            f"Hai raggiunto il limite giornaliero di {limit} {label}. Riprova domani."
        )


def _local_date_str(user_timezone: str) -> str:
    try:
        tz = ZoneInfo(user_timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).strftime("%Y-%m-%d")


def check_and_increment(user_id: int, kind: str, limit: int, user_timezone: str = "UTC") -> None:
    """kind: 'generation' o 'evaluation'. Solleva RateLimitExceeded se il
    limite giornaliero (calcolato sul fuso orario locale dell'utente) è già
    stato raggiunto; altrimenti incrementa il contatore e lascia proseguire.
    Bypassabile in dev con RATE_LIMIT_ENABLED=False."""
    if not config("RATE_LIMIT_ENABLED", default=True, cast=bool):
        return

    date_str = _local_date_str(user_timezone)
    key = f"ratelimit:{kind}:{user_id}:{date_str}"

    client = get_redis_client()
    current = client.get(key)
    current = int(current) if current is not None else 0

    if current >= limit:
        raise RateLimitExceeded(kind, limit)

    pipe = client.pipeline()
    pipe.incr(key)
    if current == 0:
        pipe.expire(key, 60 * 60 * 26)  # margine oltre le 24h
    pipe.execute()
