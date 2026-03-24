from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from .models import Bill, BillStatus
from .scrapers import upsert_bills
from .services import update_bill_status


class BillStatusNotificationTests(TestCase):
    def setUp(self):
        self.bill = Bill.objects.create(
            id="test-bill",
            title="Test Bill",
            summary="A short summary for testing SMS notifications.",
            status=BillStatus.FIRST_READING,
            category="Finance",
            date_introduced=date(2026, 1, 1),
            is_hot=False,
        )

    def test_update_bill_status_queues_automatic_sms_broadcast(self):
        with patch("apps.legislative.services.broadcast_bill_update") as broadcast_mock:
            with self.captureOnCommitCallbacks(execute=True):
                update_bill_status(
                    self.bill,
                    BillStatus.SECOND_READING,
                    previous_status=BillStatus.FIRST_READING,
                    actor="admin",
                )

        broadcast_mock.assert_called_once()
        _, message = broadcast_mock.call_args.args
        self.assertIn(self.bill.title, message)
        self.assertIn("First Reading -> Second Reading", message)

    def test_scraper_upsert_triggers_status_change_hook(self):
        with patch("apps.legislative.scrapers.update_bill_status") as status_mock:
            summary = upsert_bills(
                [
                    {
                        "id": self.bill.id,
                        "title": self.bill.title,
                        "summary": self.bill.summary,
                        "status": BillStatus.SECOND_READING,
                        "category": self.bill.category,
                        "date_introduced": self.bill.date_introduced,
                        "is_hot": self.bill.is_hot,
                        "parliament_url": "https://example.com/bill",
                        "key_points": [],
                        "timeline": [],
                    }
                ]
            )

        self.assertEqual(summary["updated"], 1)
        status_mock.assert_called_once()
        call_args = status_mock.call_args
        self.assertEqual(call_args.args[0].pk, self.bill.pk)
        self.assertEqual(call_args.args[1], BillStatus.SECOND_READING)
        self.assertEqual(call_args.kwargs["previous_status"], BillStatus.FIRST_READING)
        self.assertEqual(call_args.kwargs["actor"], "scrape")
