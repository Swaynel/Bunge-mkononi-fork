"""
Process PDF bill documents into structured text.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

from apps.legislative.models import Bill
from apps.legislative.services import process_bill_document
from apps.legislative.document_processing import resolve_bill_pdf_url


REQUIRED_DOCUMENT_COLUMNS = {
    "document_status",
    "document_method",
    "document_source_url",
    "document_text",
    "document_pages",
    "document_error",
    "document_page_count",
    "document_word_count",
    "document_processed_at",
}


class Command(BaseCommand):
    help = "Extract text from bill PDFs and store the structured output on each Bill."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bill-id",
            action="append",
            dest="bill_ids",
            help="Process a single bill id. Repeat the flag to process multiple bills.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Reprocess even if the bill already has structured document content.",
        )

    def _ensure_document_schema(self) -> None:
        try:
            with connection.cursor() as cursor:
                columns = {
                    column.name
                    for column in connection.introspection.get_table_description(cursor, Bill._meta.db_table)
                }
        except (OperationalError, ProgrammingError) as exc:
            raise CommandError(
                "Unable to inspect the database. Make sure Postgres is running, then run "
                "`python manage.py migrate` before processing bill documents."
            ) from exc

        missing_columns = REQUIRED_DOCUMENT_COLUMNS - columns
        if missing_columns:
            missing_list = ", ".join(sorted(missing_columns))
            raise CommandError(
                "The bill document fields have not been applied to the database yet. "
                f"Missing columns: {missing_list}. Run `python manage.py migrate` first."
            )

    def handle(self, *args, **options):
        bill_ids = options.get("bill_ids") or []
        force = bool(options.get("force"))

        self._ensure_document_schema()

        queryset = Bill.objects.select_related().order_by("-date_introduced", "title")
        if bill_ids:
            queryset = queryset.filter(pk__in=bill_ids)

        ready_count = 0
        needs_ocr_count = 0
        failed_count = 0
        skipped_count = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Processing bill documents"))

        for bill in queryset.iterator():
            source_url = resolve_bill_pdf_url(bill.full_text_url, bill.parliament_url)
            if not source_url and not force:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"[skip] {bill.id} - {bill.title} (no PDF source)"))
                continue

            result = process_bill_document(bill, force=force)
            status = str(result.get("status") or "").lower()

            if status == "ready":
                ready_count += 1
                self.stdout.write(self.style.SUCCESS(f"[ready] {bill.id} - {bill.title}"))
            elif status == "needs_ocr":
                needs_ocr_count += 1
                self.stdout.write(self.style.WARNING(f"[needs_ocr] {bill.id} - {bill.title}"))
            elif status == "failed":
                failed_count += 1
                error = str(result.get("error") or "Unknown error").strip()
                self.stdout.write(self.style.ERROR(f"[failed] {bill.id} - {bill.title}: {error}"))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"[skip] {bill.id} - {bill.title}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"ready      : {ready_count}"))
        self.stdout.write(self.style.WARNING(f"needs_ocr  : {needs_ocr_count}"))
        self.stdout.write(self.style.ERROR(f"failed     : {failed_count}"))
        self.stdout.write(self.style.SUCCESS(f"skipped    : {skipped_count}"))
