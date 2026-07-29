import logging

import httpx
from decouple import config

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_expo_push(token: str, title: str, body: str) -> None:
    access_token = config("EXPO_ACCESS_TOKEN", default="")
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    payload = {"to": token, "title": title, "body": body}

    try:
        response = httpx.post(EXPO_PUSH_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Invio notifica push fallito (errore HTTP) per token %s: %s", token, exc)
        return

    data = response.json().get("data", {})
    if data.get("status") == "error":
        logger.error(
            "Invio notifica push fallito per token %s: %s",
            token, data.get("message", "errore sconosciuto"),
        )
