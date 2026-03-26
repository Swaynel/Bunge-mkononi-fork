from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
from typing import Any, Protocol, cast

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.legislative.representative_scrapers import (
    MP_URL,
    MP_URL_ALTERNATES,
    _parse_member_cards,
    scrape_representatives as scrape_member_representatives,
)

from .models import Bill, BillStatus, Representative, RepresentativeVote, VoteChoice
from .models import Subscription, SubscriptionScope, SubscriptionStatus
from .services import process_bill_document
from .views import BillViewSet, BillVoteSummaryAPIView, BillVotesAPIView, RepresentativeViewSet, SmsInboundAPIView, UssdCallbackAPIView
from .scrapers import upsert_bills
from .services import create_subscription, update_bill_status


class SupportsCommitCallbacks(Protocol):
    def captureOnCommitCallbacks(self, *, execute: bool = False) -> Any: ...


class CommitCallbacksMixin:
    def capture_on_commit_callbacks(self, execute: bool = False) -> Any:
        testcase = cast(SupportsCommitCallbacks, self)
        return testcase.captureOnCommitCallbacks(execute=execute)


def response_data(response: Any) -> Any:
    return cast(Any, response).data


class BillStatusNotificationTests(CommitCallbacksMixin, TestCase):
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
            with self.capture_on_commit_callbacks(execute=True):
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

    def test_scraper_upsert_triggers_document_processing(self):
        with patch("apps.legislative.scrapers.process_bill_document") as document_mock:
            document_mock.return_value = {
                "status": "ready",
                "method": "text",
                "sourceUrl": "https://www.parliament.go.ke/example.pdf",
                "text": "Example text",
                "pages": [],
                "pageCount": 1,
                "wordCount": 2,
                "error": "",
            }

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
                        "parliament_url": "https://www.parliament.go.ke/sites/default/files/2025-09/example.pdf",
                        "key_points": [],
                        "timeline": [],
                    }
                ]
            )

        self.assertEqual(summary["updated"], 1)
        document_mock.assert_called_once()
        self.assertEqual(document_mock.call_args.args[0].pk, self.bill.pk)


class BillDocumentProcessingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bill = Bill.objects.create(
            id="document-bill",
            title="Document Bill",
            summary="A bill used to test extracted document storage.",
            status=BillStatus.FIRST_READING,
            category="Justice",
            date_introduced=date(2026, 1, 15),
            is_hot=False,
            full_text_url="https://www.parliament.go.ke/sites/default/files/2025-09/example.pdf",
        )

    def test_process_bill_document_persists_structured_content(self):
        with patch("apps.legislative.services.analyze_pdf_document") as analyze_mock:
            analyze_mock.return_value = {
                "status": "ready",
                "method": "text",
                "sourceUrl": self.bill.full_text_url,
                "text": "An Act of Parliament to make provision for testing.",
                "pages": [
                    {
                        "pageNumber": 1,
                        "blocks": [
                            {"type": "heading", "text": "AN ACT", "level": 1},
                            {"type": "paragraph", "text": "An Act of Parliament to make provision for testing."},
                        ],
                    }
                ],
                "pageCount": 1,
                "wordCount": 9,
                "error": "",
            }

            result = process_bill_document(self.bill, force=True)

        self.bill = Bill.objects.get(pk=self.bill.pk)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(self.bill.document_status, "ready")
        self.assertEqual(self.bill.document_method, "text")
        self.assertEqual(self.bill.document_source_url, self.bill.full_text_url)
        self.assertEqual(self.bill.document_page_count, 1)
        self.assertEqual(self.bill.document_word_count, 9)
        self.assertEqual(self.bill.document_pages[0]["pageNumber"], 1)
        self.assertIn("testing", self.bill.document_text)

    def test_bill_detail_endpoint_includes_document_fields(self):
        self.bill.document_status = "ready"
        self.bill.document_method = "text"
        self.bill.document_source_url = self.bill.full_text_url
        self.bill.document_text = "Structured bill text"
        self.bill.document_pages = [
            {
                "pageNumber": 1,
                "blocks": [{"type": "paragraph", "text": "Structured bill text"}],
            }
        ]
        self.bill.document_error = ""
        self.bill.document_page_count = 1
        self.bill.document_word_count = 3
        self.bill.save(
            update_fields=[
                "document_status",
                "document_method",
                "document_source_url",
                "document_text",
                "document_pages",
                "document_error",
                "document_page_count",
                "document_word_count",
            ]
        )

        request = self.factory.get(f"/api/bills/{self.bill.pk}/")
        response = BillViewSet.as_view({"get": "retrieve"})(request, pk=self.bill.pk)
        data = response_data(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["documentStatus"], "ready")
        self.assertEqual(data["documentMethod"], "text")
        self.assertIn("documentPages", data)
        self.assertEqual(data["documentPages"][0]["pageNumber"], 1)


class BillSearchTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bill = Bill.objects.create(
            id="searchable-bill",
            title="Completely Different Title",
            summary="Another unrelated summary for bill search tests.",
            status=BillStatus.COMMITTEE,
            category="Environment",
            sponsor="Hon. Alice Wanjiku",
            date_introduced=date(2026, 2, 1),
            is_hot=False,
        )

    def test_bill_list_search_matches_multiple_bill_fields(self):
        search_terms = [
            ("searchable-bill", "id"),
            ("committee", "status"),
            ("environment", "category"),
            ("wanjiku", "sponsor"),
            ("unrelated summary", "summary"),
        ]

        for term, field_name in search_terms:
            with self.subTest(field=field_name):
                request = self.factory.get("/api/bills/", {"search": term})
                response = BillViewSet.as_view({"get": "list"})(request)
                data = response_data(response)

                self.assertEqual(response.status_code, 200)
                result_ids = [item["id"] for item in data["results"]]
                self.assertIn(self.bill.pk, result_ids)


class RepresentativeVotingApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bill = Bill.objects.create(
            id="vote-bill",
            title="Vote Bill",
            summary="A bill used to test vote endpoints.",
            status=BillStatus.SECOND_READING,
            category="Justice",
            date_introduced=date(2026, 3, 1),
            is_hot=False,
        )
        self.mp = Representative.objects.create(
            id="hon-wanjiku",
            name="Hon. Alice Wanjiku",
            role="MP",
            constituency="Westlands",
            county="Nairobi",
            party="UDA",
            image_url="",
        )
        self.senator = Representative.objects.create(
            id="sen-kimani",
            name="Hon. Brian Kimani",
            role="Senator",
            constituency="Nairobi",
            county="Nairobi",
            party="ODM",
            image_url="",
        )
        RepresentativeVote.objects.create(representative=self.mp, bill=self.bill, vote=VoteChoice.YES)
        RepresentativeVote.objects.create(representative=self.senator, bill=self.bill, vote=VoteChoice.NO)

    def test_representative_list_filters_by_role_and_bill(self):
        request = self.factory.get("/api/representatives/", {"role": "MP", "billId": self.bill.pk})
        response = RepresentativeViewSet.as_view({"get": "list"})(request)
        data = response_data(response)

        self.assertEqual(response.status_code, 200)
        result_ids = [item["id"] for item in data["results"]]
        self.assertEqual(result_ids, [self.mp.id])

    def test_bill_votes_endpoint_filters_and_enriches_representatives(self):
        request = self.factory.get(f"/api/bills/{self.bill.pk}/votes/", {"vote": "Yes"})
        response = BillVotesAPIView.as_view()(request, bill_id=self.bill.pk)
        data = response_data(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["billId"], self.bill.pk)
        self.assertEqual(data["totalVotes"], 1)
        vote = data["votes"][0]
        self.assertEqual(vote["vote"], "Yes")
        self.assertEqual(vote["representative"]["role"], "MP")
        self.assertEqual(vote["representative"]["county"], "Nairobi")

    def test_bill_vote_summary_endpoint_aggregates_by_county_and_party(self):
        request = self.factory.get(f"/api/bills/{self.bill.pk}/votes/summary/")
        response = BillVoteSummaryAPIView.as_view()(request, bill_id=self.bill.pk)
        data = response_data(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["billId"], self.bill.pk)
        self.assertEqual(data["yes"], 1)
        self.assertEqual(data["no"], 1)
        self.assertEqual(data["abstain"], 0)
        self.assertEqual(data["byCounty"][0]["county"], "Nairobi")
        self.assertIn("UDA", data["byParty"])
        self.assertIn("ODM", data["byParty"])


class RepresentativeScraperParsingTests(TestCase):
    def test_views_row_title_attribute_is_used_for_name_and_constituency(self):
        html = """
            <html>
                <body>
                    <div class="views-row">
                        <div class="views-field views-field-title">
                            <a href="/member/hon-jane-doe" title="Hon. Jane Doe, Westlands, UDA">More Info</a>
                        </div>
                        <div class="views-field views-field-field-constituency">Westlands</div>
                        <div class="views-field views-field-field-party">UDA</div>
                        <div class="views-field views-field-field-status">Elected</div>
                    </div>
                </body>
            </html>
        """

        members = _parse_member_cards(html, base_url=MP_URL, role="MP")

        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["name"], "Hon. Jane Doe")
        self.assertEqual(members[0]["constituency"], "Westlands")
        self.assertEqual(members[0]["county"], "Nairobi")
        self.assertEqual(members[0]["party"], "UDA")

    def test_mp_scraper_falls_back_to_index_php_url_when_primary_404s(self):
        primary_url = MP_URL
        fallback_url = MP_URL_ALTERNATES[1]
        html = """
            <html>
                <body>
                    <div class="views-row">
                        <div class="views-field views-field-title">
                            <a href="/member/hon-jane-doe" title="Hon. Jane Doe, Westlands, UDA">More Info</a>
                        </div>
                        <div class="views-field views-field-field-constituency">Westlands</div>
                        <div class="views-field views-field-field-party">UDA</div>
                    </div>
                </body>
            </html>
        """

        parsed_members = [
            {
                "id": "hon-jane-doe",
                "name": "Hon. Jane Doe",
                "role": "MP",
                "constituency": "Westlands",
                "county": "Nairobi",
                "party": "UDA",
                "image_url": "",
            }
        ]

        def fetch_side_effect(url: str, timeout: int, progress=None):
            if url == primary_url:
                return [], [f"Failed to fetch {primary_url}: 404"]
            if url == fallback_url:
                return [(fallback_url, html)], []
            self.fail(f"Unexpected URL requested: {url}")

        with patch("representative_scrapers._fetch_all_pages", side_effect=fetch_side_effect) as fetch_mock:
            with patch("representative_scrapers._parse_member_cards", return_value=parsed_members):
                with patch(
                    "representative_scrapers._upsert_representatives",
                    return_value={
                        "created": 1,
                        "updated": 0,
                        "errors": [],
                        "processed": [{"id": "hon-jane-doe", "name": "Hon. Jane Doe", "action": "created"}],
                    },
                ):
                    summary = scrape_member_representatives(role="MP", timeout=1)

        self.assertEqual(summary["url"], fallback_url)
        self.assertEqual(summary["members_found"], 1)
        self.assertGreaterEqual(fetch_mock.call_count, 2)
        self.assertEqual(fetch_mock.call_args_list[0].args[0], primary_url)
        self.assertEqual(fetch_mock.call_args_list[1].args[0], fallback_url)


class UssdMenuTests(CommitCallbacksMixin, TestCase):
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
            with self.capture_on_commit_callbacks(execute=True):
                subscription, created, reactivated = create_subscription(bill, "+254700000000", "ussd")

        self.assertTrue(created)
        self.assertFalse(reactivated)
        self.assertIsNotNone(subscription.bill)
        self.assertEqual(subscription.bill.pk, bill.pk)
        send_sms_mock.assert_called_once()
        message, recipients = send_sms_mock.call_args.args[:2]
        self.assertIn(bill.title, message)
        self.assertIn(f"STATUS {bill.id}", message)
        self.assertEqual(recipients, [subscription.phone_number])

    def test_ussd_follow_all_bills_creates_watchlist_subscription(self):
        request = self.factory.post("/api/ussd/", {"text": "3*5", "phoneNumber": "+254700000000"}, format="json")

        with patch("apps.legislative.services.send_sms") as send_sms_mock:
            with self.capture_on_commit_callbacks(execute=True):
                response = UssdCallbackAPIView.as_view()(request)

        body = response.content.decode()
        self.assertIn("SMS confirmation", body)
        subscription = Subscription.objects.get(phone_number="+254700000000", scope=SubscriptionScope.ALL)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.target_value, "")
        send_sms_mock.assert_called_once()


class SmsWebhookTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.bill = Bill.objects.create(
            id="sms-bill",
            title="SMS Bill",
            summary="A bill used to test SMS webhook idempotency.",
            status=BillStatus.FIRST_READING,
            category="Finance",
            date_introduced=date(2026, 4, 1),
            is_hot=False,
        )

    def test_sms_inbound_webhook_is_idempotent(self):
        payload = {"from": "+254700000000", "text": f"DOCUMENT {self.bill.pk}"}

        first_request = self.factory.post("/api/sms/inbound/", payload, format="json")
        second_request = self.factory.post("/api/sms/inbound/", payload, format="json")

        first_response = SmsInboundAPIView.as_view()(first_request)
        second_response = SmsInboundAPIView.as_view()(second_request)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.content, second_response.content)
        self.assertIn("Bill ID: sms-bill", first_response.content.decode())
