"""
backend/apps/legislative/management/commands/scrape_representatives.py

Django management command to scrape Kenyan MPs, Senators, and their voting
records from parliament.go.ke.

Usage:
    python manage.py scrape_representatives
    python manage.py scrape_representatives --role MP
    python manage.py scrape_representatives --role Senator
    python manage.py scrape_representatives --role MP --url https://...
    python manage.py scrape_representatives --votes-bill finance-bill-2026 --votes-url https://...
    python manage.py scrape_representatives --dry-run
"""

from django.core.management.base import BaseCommand, CommandError

from apps.legislative.representative_scrapers import (
    _candidate_member_urls,
    MP_URL,
    SENATOR_URL,
    DEFAULT_TIMEOUT,
    scrape_all,
    scrape_representative_votes,
    scrape_representatives,
)


class Command(BaseCommand):
    help = "Scrape Kenyan MPs/Senators and their bill votes from parliament.go.ke."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            choices=["MP", "Senator", "all"],
            default="all",
            help="Which role to scrape: MP, Senator, or all (default: all).",
        )
        parser.add_argument(
            "--url",
            default="",
            help="Override the default parliament members page URL.",
        )
        parser.add_argument(
            "--votes-bill",
            dest="votes_bill",
            default="",
            help="Bill ID to associate voting records with (e.g. finance-bill-2026).",
        )
        parser.add_argument(
            "--votes-url",
            dest="votes_url",
            default="",
            help="URL of the Hansard division/votes page for the specified bill.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT,
            help=f"HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and print results without writing to the database.",
        )

    def handle(self, *args, **options):
        role = options["role"]
        url = options["url"]
        votes_bill = options["votes_bill"]
        votes_url = options["votes_url"]
        timeout = options["timeout"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database writes."))

        # ── Scrape members ────────────────────────────────────────────────
        if not votes_bill:
            self._scrape_members(role, url, timeout, dry_run)

        # ── Scrape votes for a specific bill ──────────────────────────────
        if votes_bill:
            if not votes_url:
                raise CommandError("--votes-url is required when --votes-bill is specified.")
            self._scrape_votes(votes_bill, votes_url, timeout, dry_run)

    def _scrape_members(self, role: str, url: str, timeout: int, dry_run: bool):
        from apps.legislative.representative_scrapers import (  # noqa: PLC0415
            _fetch_all_pages,
            _parse_member_cards,
        )

        if dry_run:
            roles_to_scrape = (
                [("MP", _candidate_member_urls("MP", url)), ("Senator", _candidate_member_urls("Senator", url))]
                if role == "all"
                else [(role, _candidate_member_urls(role, url))]
            )

            def fetch_member_pages(candidate_urls: list[str]) -> tuple[str, list[tuple[str, str]], list[str]]:
                pages: list[tuple[str, str]] = []
                errors: list[str] = []
                selected_url = candidate_urls[0]
                for candidate_url in candidate_urls:
                    selected_url = candidate_url
                    self.stdout.write(f"  Fetching {candidate_url}...")
                    candidate_pages, candidate_errors = _fetch_all_pages(candidate_url, timeout=timeout)
                    errors.extend(candidate_errors)
                    if candidate_pages:
                        pages = candidate_pages
                        break
                return selected_url, pages, errors

            for r, candidate_urls in roles_to_scrape:
                try:
                    selected_url, pages, errors = fetch_member_pages(candidate_urls)
                    members: list[dict] = []
                    seen: set[str] = set()
                    self.stdout.write(self.style.MIGRATE_HEADING(
                        f"DRY RUN: Scraping {r} members from: {selected_url}"
                    ))
                    for page_url, html in pages:
                        for m in _parse_member_cards(html, base_url=page_url, role=r):
                            if m["id"] not in seen:
                                seen.add(m["id"])
                                members.append(m)
                except Exception as exc:  # noqa: BLE001
                    raise CommandError(f"Scrape failed: {exc}") from exc

                self.stdout.write(f"Found {len(members)} {r}(s) across {len(pages)} page(s):\n")
                for member in members[:20]:  # cap output for readability
                    const = member.get("constituency", "-")
                    county = member.get("county", "-")
                    party = member.get("party", "-")
                    self.stdout.write(
                        f"  {member['name']:<40} {const:<25} {county:<20} {party}"
                    )
                if len(members) > 20:
                    self.stdout.write(f"  ... and {len(members) - 20} more.")
                if errors:
                    for err in errors:
                        self.stdout.write(self.style.WARNING(f"  WARN: {err}"))
            return

        # Live run
        if role == "all":
            self.stdout.write(self.style.MIGRATE_HEADING("Scraping all members (MPs + Senators)..."))
            try:
                summary = scrape_all(
                    timeout=timeout,
                    progress=lambda fetched_url: self.stdout.write(f"  Fetching {fetched_url}..."),
                )
            except Exception as exc:  # noqa: BLE001
                raise CommandError(f"Scrape failed: {exc}") from exc

            self._print_member_summary("MP", summary["mp"])
            self._print_member_summary("Senator", summary["senator"])
            self.stdout.write(self.style.SUCCESS(
                f"\nTotal: {summary['total_members_found']} found, "
                f"{summary['total_created']} created, "
                f"{summary['total_updated']} updated"
            ))
        else:
            target_url = url or (MP_URL if role == "MP" else SENATOR_URL)
            self.stdout.write(self.style.MIGRATE_HEADING(f"Scraping {role} members from: {target_url}"))
            try:
                summary = scrape_representatives(
                    url=target_url,
                    role=role,
                    timeout=timeout,
                    progress=lambda fetched_url: self.stdout.write(f"  Fetching {fetched_url}..."),
                )
            except Exception as exc:  # noqa: BLE001
                raise CommandError(f"Scrape failed: {exc}") from exc
            self._print_member_summary(role, summary)

    def _print_member_summary(self, role: str, summary: dict):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"[{role}] Members found  : {summary['members_found']}"))
        self.stdout.write(self.style.SUCCESS(f"[{role}] Pages fetched  : {summary['pages_fetched']}"))
        self.stdout.write(self.style.SUCCESS(f"[{role}] Created        : {summary['created']}"))
        self.stdout.write(self.style.SUCCESS(f"[{role}] Updated        : {summary['updated']}"))
        if summary.get("errors"):
            for err in summary["errors"]:
                self.stdout.write(self.style.WARNING(f"[{role}] WARN: {err}"))

    def _scrape_votes(self, bill_id: str, votes_url: str, timeout: int, dry_run: bool):
        from apps.legislative.representative_scrapers import (  # noqa: PLC0415
            _get,
            _parse_division_votes,
        )

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Scraping votes for bill '{bill_id}' from: {votes_url}"
        ))

        if dry_run:
            try:
                html = _get(votes_url, timeout=timeout)
                votes = _parse_division_votes(html, base_url=votes_url)
            except Exception as exc:  # noqa: BLE001
                raise CommandError(f"Vote scrape failed: {exc}") from exc

            self.stdout.write(f"Found {len(votes)} vote record(s):\n")
            for v in votes[:30]:
                self.stdout.write(f"  {v['name']:<40} {v['vote']}")
            if len(votes) > 30:
                self.stdout.write(f"  ... and {len(votes) - 30} more.")
            return

        try:
            summary = scrape_representative_votes(bill_id=bill_id, url=votes_url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Vote scrape failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Votes found    : {summary['votes_found']}"))
        self.stdout.write(self.style.SUCCESS(f"Created        : {summary['created']}"))
        self.stdout.write(self.style.SUCCESS(f"Updated        : {summary['updated']}"))
        self.stdout.write(self.style.SUCCESS(f"Unmatched      : {summary.get('unmatched', 0)}"))
        if summary.get("errors"):
            for err in summary["errors"][:10]:
                self.stdout.write(self.style.WARNING(f"WARN: {err}"))
