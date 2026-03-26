"""
Remove old outbound message and webhook receipt records.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.legislative.models import OutboundMessage, OutboundMessageStatus, WebhookReceipt


class Command(BaseCommand):
    help = "Delete stale outbound message and webhook receipt audit rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Remove records older than this many days.",
        )

    def handle(self, *args, **options):
        days = int(options.get("days") or 90)
        cutoff = timezone.now() - timedelta(days=days)

        webhook_deleted = WebhookReceipt.objects.filter(created_at__lt=cutoff).delete()[0]
        outbound_deleted = OutboundMessage.objects.filter(
            created_at__lt=cutoff,
            status__in=[
                OutboundMessageStatus.ACCEPTED,
                OutboundMessageStatus.SENT,
                OutboundMessageStatus.FAILED,
                OutboundMessageStatus.UNDELIVERED,
                OutboundMessageStatus.SKIPPED,
            ],
        ).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {outbound_deleted} outbound message(s) and {webhook_deleted} webhook receipt(s)."
            )
        )
