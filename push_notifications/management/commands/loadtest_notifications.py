"""
Nuovo file: remembro-backend/push_notifications/management/commands/loadtest_notifications.py

Fase 15, punto 3 — test di carico leggero sul job di scheduling.

Crea N utenti sintetici, ciascuno con M card scadute, ed esegue
send_due_review_notifications() misurando tempo e numero di query.
Serve a quantificare il problema noto delle query N+1 (oggi il task
cicla sugli utenti e per ognuno interroga il database) e ad avere un
numero di riferimento prima di decidere se e quando ottimizzare.

Due protezioni:
- send_expo_push è mockato: nessuna notifica reale viene inviata.
- tutto gira in una transazione con rollback finale: il database resta
  invariato, i dati sintetici non restano.

Nessuna chiamata AI, quindi costo zero.

Esempi:
    python manage.py loadtest_notifications
    python manage.py loadtest_notifications --users 500 --cards 20
"""
import time
from datetime import time as dtime
from unittest.mock import patch

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone as djtz

from authentication.models import NotificationSettings
from cards.models import Card
from categories.models import Category
from notions.models import Notion
from push_notifications.tasks import send_due_review_notifications


class Command(BaseCommand):
    help = "Test di carico del job notifiche: misura tempo e query con N utenti sintetici."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=200, help="Numero di utenti sintetici.")
        parser.add_argument("--cards", type=int, default=10, help="Card scadute per utente.")
        parser.add_argument(
            "--categories",
            type=int,
            default=2,
            help="Categorie per utente (piu' di 1 attiva il ramo di aggregazione).",
        )

    def handle(self, *args, **options):
        n_users = options["users"]
        n_cards = options["cards"]
        n_cats = max(1, options["categories"])

        now = djtz.now()
        # Tutti gli utenti in UTC con orario preferito = ora corrente,
        # cosi' il job li considera tutti idonei e misuriamo il caso peggiore.
        current_hour = dtime(hour=now.hour)
        past = now - djtz.timedelta(days=1)

        User = get_user_model()

        with transaction.atomic():
            self.stdout.write(f"Creazione di {n_users} utenti x {n_cards} card ...")
            setup_started = time.monotonic()

            users = User.objects.bulk_create([
                User(username=f"_loadtest_u{i}", email=f"_loadtest_u{i}@example.invalid")
                for i in range(n_users)
            ])
            NotificationSettings.objects.bulk_create([
                NotificationSettings(
                    user=u,
                    expo_push_token=f"ExponentPushToken[_loadtest_{u.pk}]",
                    timezone="UTC",
                    preferred_time=current_hour,
                )
                for u in users
            ])
            categories = Category.objects.bulk_create([
                Category(user=u, name=f"Cat{c}")
                for u in users
                for c in range(n_cats)
            ])
            notions = Notion.objects.bulk_create([
                Notion(
                    user=cat.user,
                    category=cat,
                    raw_content="Contenuto sintetico per il test di carico.",
                )
                for cat in categories
            ])
            per_notion = max(1, n_cards // n_cats)
            Card.objects.bulk_create([
                Card(
                    notion=n,
                    card_type=Card.CardType.ATOMIC_QA,
                    question="?",
                    key_points=["a", "b"],
                    status=Card.Status.ACTIVE,
                    interval_index=1,
                    next_review_at=past,
                )
                for n in notions
                for _ in range(per_notion)
            ])
            setup_elapsed = time.monotonic() - setup_started
            self.stdout.write(f"  setup completato in {setup_elapsed:.1f}s")

            self.stdout.write("Esecuzione del job (push mockate) ...")
            with patch("push_notifications.tasks.send_expo_push") as mock_send:
                with CaptureQueriesContext(connection) as ctx:
                    started = time.monotonic()
                    send_due_review_notifications()
                    elapsed = time.monotonic() - started

            n_queries = len(ctx.captured_queries)
            n_sent = mock_send.call_count

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Risultati"))
            self.stdout.write(f"  utenti:            {n_users}")
            self.stdout.write(f"  card per utente:   {n_cards}")
            self.stdout.write(f"  notifiche inviate: {n_sent}")
            self.stdout.write(f"  tempo job:         {elapsed:.2f}s")
            self.stdout.write(f"  query totali:      {n_queries}")
            self.stdout.write(f"  query per utente:  {n_queries / n_users:.1f}")
            self.stdout.write(f"  ms per utente:     {elapsed / n_users * 1000:.1f}")

            if n_sent != n_users:
                self.stdout.write(self.style.WARNING(
                    f"  ATTENZIONE: attese {n_users} notifiche, inviate {n_sent}"
                ))

            slowest = sorted(ctx.captured_queries, key=lambda q: float(q["time"]), reverse=True)[:3]
            self.stdout.write("")
            self.stdout.write("  Query piu' lente:")
            for q in slowest:
                self.stdout.write(f"    {q['time']}s  {q['sql'][:110]}")

            transaction.set_rollback(True)
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Rollback eseguito: nessun dato sintetico salvato."))
