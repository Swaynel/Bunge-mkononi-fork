from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Bill, BillStatus
from .views import UssdCallbackAPIView
from .scrapers import upsert_bills
from .services import create_subscription, update_bill_status


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


class UssdMenuTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bills = []
        for index in range(1, 7):
            self.bills.append(
                Bill.objects.create(
                    id=f"bill-{index}",
                    title=f"Very long parliamentary bill title number {index} that needs truncation",
                    summary="A short summary for testing USSD pagination.",
                    status=BillStatus.FIRST_READING,
                    category="Finance",
                    date_introduced=date(2026, 1, 1) + timedelta(days=index),
                    is_hot=False,
                )
            )

    def test_ussd_bill_list_is_paginated_and_titles_are_shortened(self):
        request = self.factory.post("/api/ussd/", {"text": "1", "phoneNumber": "+254700000000"}, format="json")
        response = UssdCallbackAPIView.as_view()(request)
        body = response.content.decode()

        self.assertIn("CON Active bills (1/2)", body)
        self.assertIn("8. More", body)
        self.assertIn("...", body)

        next_request = self.factory.post("/api/ussd/", {"text": "1*8", "phoneNumber": "+254700000000"}, format="json")
        next_response = UssdCallbackAPIView.as_view()(next_request)
        next_body = next_response.content.decode()

        self.assertIn("CON Active bills (2/2)", next_body)
        self.assertIn("9. Back", next_body)
        self.assertNotIn("8. More", next_body)

    def test_ussd_subscription_sends_confirmation_sms(self):
        bill = self.bills[0]

        with patch("apps.legislative.services.send_sms") as send_sms_mock:
            with self.captureOnCommitCallbacks(execute=True):
                subscription, created = create_subscription(bill, "+254700000000", "ussd")

        self.assertTrue(created)
        self.assertEqual(subscription.bill_id, bill.pk)
        send_sms_mock.assert_called_once()
        message, recipients = send_sms_mock.call_args.args[:2]
        self.assertIn(bill.title, message)
        self.assertIn(f"STATUS {bill.id}", message)
        self.assertEqual(recipients, [subscription.phone_number])
