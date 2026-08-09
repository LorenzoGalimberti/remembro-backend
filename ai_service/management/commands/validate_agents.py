"""
Nuovo file: remembro-backend/ai_service/management/commands/validate_agents.py

Fase 15, punto 4 — validazione manuale della qualità degli agenti AI.

ATTENZIONE: questo comando usa l'API LLM REALE, quindi ha un costo vero.
Non è un test automatico (quelli usano provider mockati e restano
gratuiti): serve a produrre un report da leggere a occhio.

Chiama gli agenti direttamente, quindi bypassa view, HTTP, Celery e
rate limiting. Ma NON bypassa il tracking dei costi: ogni chiamata
riuscita scrive una riga in AIUsageLog (come farebbero le view),
attribuita all'utente passato con --user. Con --no-log si può evitare
la scrittura, per non sporcare le metriche.

Esempi:
    python manage.py validate_agents --user lorenzo
    python manage.py validate_agents --user lorenzo --limit 3
    python manage.py validate_agents --user lorenzo --only evaluation
    python manage.py validate_agents --user lorenzo --no-log --dry-run
"""
import re
import time
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ai_service.agents.evaluation import EvaluationAgent
from ai_service.agents.generation import GenerationAgent
from ai_service.exceptions import AIServiceError
from ai_service.models import AIUsageLog

from ._validation_data import EVALUATION_CASES, NOTIONS

VERDICT_WORDS = ("correct", "partial", "incorrect")


def expected_verdicts(atteso: str) -> set[str]:
    """Estrae i verdetti accettabili dal campo 'atteso'.

    Il campo è testo libero tipo "correct (nucleo colto, ...)" oppure
    "incorrect o partial (...)": prendiamo solo la parte prima della
    parentesi e cerchiamo le parole-verdetto, così un caso ambiguo
    accetta entrambi i valori.
    """
    head = atteso.split("(")[0]
    found = {w for w in VERDICT_WORDS if re.search(rf"\b{w}\b", head)}
    return found or {"?"}


class Command(BaseCommand):
    help = "Valida la qualità reale di GenerationAgent ed EvaluationAgent (usa l'API LLM vera)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Username a cui attribuire le righe di AIUsageLog.",
        )
        parser.add_argument(
            "--only",
            choices=["generation", "evaluation"],
            help="Esegue solo una delle due fasi (default: entrambe).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Usa solo i primi N casi di ogni fase (utile per una prova a basso costo).",
        )
        parser.add_argument(
            "--no-log",
            action="store_true",
            help="Non scrive in AIUsageLog (le chiamate costano comunque).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Non chiama l'API: stampa solo cosa verrebbe eseguito e quanto costerebbe di chiamate.",
        )
        parser.add_argument(
            "--output",
            help="Percorso del report markdown (default: reports/validation_<timestamp>.md).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["user"])
        except User.DoesNotExist:
            raise CommandError(f"Utente '{options['user']}' non trovato.")

        limit = options.get("limit")
        only = options.get("only")
        notions = [] if only == "evaluation" else NOTIONS[:limit]
        cases = [] if only == "generation" else EVALUATION_CASES[:limit]

        if options["dry_run"]:
            self.stdout.write(
                f"DRY RUN — verrebbero fatte {len(notions)} chiamate di generazione "
                f"e {len(cases)} di valutazione, nessuna richiesta inviata."
            )
            return

        # import qui e non in cima: get_default_provider legge la API key
        # dall'env e fallirebbe all'import in ambienti senza chiave (CI).
        from ai_service.providers import get_default_provider

        provider = get_default_provider()
        gen_agent = GenerationAgent(provider)
        eval_agent = EvaluationAgent(provider)

        lines = [
            "# Report validazione agenti AI",
            "",
            f"Data: {datetime.now():%Y-%m-%d %H:%M}",
            f"Utente AIUsageLog: {user.username}"
            + ("  (logging disattivato)" if options["no_log"] else ""),
            "",
        ]
        totals = {"prompt": 0, "completion": 0, "reasoning": 0, "total": 0, "calls": 0}
        errors = []

        # ---------- FASE 1: generazione ----------
        if notions:
            lines += ["## Generazione card", ""]
            self.stdout.write(self.style.MIGRATE_HEADING(f"Generazione: {len(notions)} nozioni"))

            for i, notion in enumerate(notions, start=1):
                label = f"[{i}/{len(notions)}] {notion['category']}"
                self.stdout.write(f"  {label} ...", ending="")
                started = time.monotonic()
                try:
                    cards = gen_agent.generate(
                        raw_content=notion["content"],
                        category_name=notion["category"],
                    )
                except AIServiceError as exc:
                    self.stdout.write(self.style.ERROR(" FALLITA"))
                    errors.append(f"generazione #{i} ({notion['category']}): {exc}")
                    lines += [f"### {i}. {notion['category']} — ERRORE", "", f"```\n{exc}\n```", ""]
                    continue
                elapsed = time.monotonic() - started
                self.stdout.write(self.style.SUCCESS(f" {len(cards)} card ({elapsed:.1f}s)"))

                self._track(provider, totals, user, AIUsageLog.CallType.GENERATION, options["no_log"])

                lines += [
                    f"### {i}. {notion['category']}",
                    "",
                    f"**Nozione:** {notion['content']}",
                    "",
                    f"**Atteso:** {notion['atteso']}",
                    "",
                    f"**Generate {len(cards)} card:**",
                    "",
                ]
                for card in cards:
                    lines += [
                        f"- **[{card['type']}]** {card['question']}",
                        "  - key_points: " + "; ".join(card["key_points"]),
                    ]
                lines += [""]

        # ---------- FASE 2: valutazione ----------
        agreement = {"ok": 0, "ko": 0}
        if cases:
            lines += ["## Valutazione risposte", ""]
            self.stdout.write(self.style.MIGRATE_HEADING(f"Valutazione: {len(cases)} casi"))

            for i, case in enumerate(cases, start=1):
                expected = expected_verdicts(case["atteso"])
                self.stdout.write(f"  [{i}/{len(cases)}] atteso={'/'.join(sorted(expected))} ...", ending="")
                try:
                    result = eval_agent.evaluate(
                        question=case["question"],
                        key_points=case["key_points"],
                        user_answer=case["answer"],
                    )
                except AIServiceError as exc:
                    self.stdout.write(self.style.ERROR(" FALLITA"))
                    errors.append(f"valutazione #{i}: {exc}")
                    lines += [f"### {i}. ERRORE", "", f"```\n{exc}\n```", ""]
                    continue

                verdict = result["verdict"]
                match = verdict in expected
                agreement["ok" if match else "ko"] += 1
                style = self.style.SUCCESS if match else self.style.WARNING
                self.stdout.write(style(f" ottenuto={verdict} {'OK' if match else 'DIVERGE'}"))

                self._track(provider, totals, user, AIUsageLog.CallType.EVALUATION, options["no_log"])

                lines += [
                    f"### {i}. {'OK' if match else 'DIVERGE'} — "
                    f"atteso {'/'.join(sorted(expected))}, ottenuto {verdict}",
                    "",
                    f"**Domanda:** {case['question']}",
                    "",
                    f"**Key points:** {'; '.join(case['key_points'])}",
                    "",
                    f"**Risposta utente:** {case['answer']}",
                    "",
                    f"**Nota attesa:** {case['atteso']}",
                    "",
                    f"**Feedback AI:** {result['feedback']}",
                    "",
                    "**Missing points:** " + ("; ".join(result["missing_points"]) or "(nessuno)"),
                    "",
                ]

        # ---------- riepilogo ----------
        summary = [
            "## Riepilogo",
            "",
            f"- Chiamate riuscite: {totals['calls']}",
            f"- Token totali: {totals['total']} "
            f"(prompt {totals['prompt']}, completion {totals['completion']}, reasoning {totals['reasoning']})",
        ]
        if cases:
            done = agreement["ok"] + agreement["ko"]
            pct = (agreement["ok"] / done * 100) if done else 0
            summary.append(f"- Accordo verdetti: {agreement['ok']}/{done} ({pct:.0f}%)")
        if errors:
            summary += ["- Errori:", ""] + [f"  - {e}" for e in errors]
        summary.append("")
        lines = lines[:4] + summary + lines[4:]

        out_path = Path(options["output"] or f"reports/validation_{datetime.now():%Y%m%d_%H%M}.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write("")
        for line in summary:
            if line:
                self.stdout.write(line.replace("- ", "").replace("#", "").strip())
        self.stdout.write(self.style.SUCCESS(f"\nReport salvato in: {out_path}"))

    def _track(self, provider, totals, user, call_type, no_log):
        """Aggiorna i totali e (se richiesto) scrive la riga in AIUsageLog."""
        usage = getattr(provider, "last_usage", None)
        if not usage:
            return
        totals["calls"] += 1
        totals["prompt"] += usage["prompt_tokens"]
        totals["completion"] += usage["completion_tokens"]
        totals["reasoning"] += usage["reasoning_tokens"] or 0
        totals["total"] += usage["total_tokens"]
        if no_log:
            return
        AIUsageLog.objects.create(
            user=user,
            call_type=call_type,
            model=usage["model"],
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            reasoning_tokens=usage["reasoning_tokens"],
            total_tokens=usage["total_tokens"],
        )
