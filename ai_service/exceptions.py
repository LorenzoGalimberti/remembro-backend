class AIServiceError(Exception):
    """Sollevata quando una chiamata AI fallisce (o produce output non valido)
    dopo il singolo retry previsto. Nessun fallback silenzioso: l'errore va
    propagato al chiamante (task/endpoint)."""
    pass
