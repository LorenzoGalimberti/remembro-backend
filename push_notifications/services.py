"""
Sostituisce interamente: remembro-backend/push_notifications/services.py

Aggiunta: send_expo_push accetta un parametro opzionale data (dizionario),
incluso nel payload Expo solo se presente. Serve al mobile per sapere
quale categoria aprire quando l'utente tocca la notifica.
"""

import logging

import httpx
from decouple import config

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_expo_push(token: str, title: str, body: str, data: dict | None = None) -> None:
    access_token = config("EXPO_ACCESS_TOKEN", default="")
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    payload = {"to": token, "title": title, "body": body}
    if data:
        payload["data"] = data

    try:
        response = httpx.post(EXPO_PUSH_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Invio notifica push fallito (errore HTTP) per token %s: %s", token, exc)
        return

    data_response = response.json().get("data", {})
    if data_response.get("status") == "error":
        logger.error(
            "Invio notifica push fallito per token %s: %s",
            token, data_response.get("message", "errore sconosciuto"),
        )