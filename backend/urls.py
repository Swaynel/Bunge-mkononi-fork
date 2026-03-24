"""
backend/apps/legislative/urls.py  (updated — replaces existing file)

Adds the four new Leaders / Voting endpoints:
  POST /api/scrape/representatives/        — trigger member scrape
  POST /api/scrape/votes/                  — trigger vote scrape for a bill
  GET  /api/bills/{bill_id}/votes/         — all votes on a bill
  GET  /api/bills/{bill_id}/votes/summary/ — aggregated vote tally

All existing routes are unchanged.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminMetricsAPIView,
    BillViewSet,
    BillVotesAPIView,
    BillVoteSummaryAPIView,
    CountyStatViewSet,
    DashboardAPIView,
    HealthCheckAPIView,
    PetitionViewSet,
    PollResponseViewSet,
    RepresentativeViewSet,
    ScrapeBillsAPIView,
    ScrapeHistoryAPIView,
    ScrapeRepresentativesAPIView,
    ScrapeVotesAPIView,
    SmsDeliveryReportAPIView,
    SmsInboundAPIView,
    SubscriptionViewSet,
    SystemLogViewSet,
    UssdCallbackAPIView,
)

router = DefaultRouter()
router.register("bills", BillViewSet, basename="bills")
router.register("petitions", PetitionViewSet, basename="petitions")
router.register("representatives", RepresentativeViewSet, basename="representatives")
router.register("counties", CountyStatViewSet, basename="counties")
router.register("votes", PollResponseViewSet, basename="votes")
router.register("subscriptions", SubscriptionViewSet, basename="subscriptions")
router.register("logs", SystemLogViewSet, basename="logs")

urlpatterns = [
    # ── Utility / health ──────────────────────────────────────────────────
    path("health/", HealthCheckAPIView.as_view(), name="health"),
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),

    # ── Bills — vote sub-resources (MUST be before router.urls) ──────────
    path(
        "bills/<str:bill_id>/votes/summary/",
        BillVoteSummaryAPIView.as_view(),
        name="bill-votes-summary",
    ),
    path(
        "bills/<str:bill_id>/votes/",
        BillVotesAPIView.as_view(),
        name="bill-votes",
    ),

    # ── Scraper endpoints ─────────────────────────────────────────────────
    path("scrape/", ScrapeBillsAPIView.as_view(), name="scrape-bills"),
    path("scrape/history/", ScrapeHistoryAPIView.as_view(), name="scrape-history"),
    path("scrape/representatives/", ScrapeRepresentativesAPIView.as_view(), name="scrape-representatives"),
    path("scrape/votes/", ScrapeVotesAPIView.as_view(), name="scrape-votes"),

    # ── Admin metrics ─────────────────────────────────────────────────────
    path("admin/metrics/", AdminMetricsAPIView.as_view(), name="admin-metrics"),

    # ── Africa's Talking integrations ─────────────────────────────────────
    path("track/", SubscriptionViewSet.as_view({"post": "create"}), name="track"),
    path("sms/inbound/", SmsInboundAPIView.as_view(), name="sms-inbound"),
    path("sms/delivery/", SmsDeliveryReportAPIView.as_view(), name="sms-delivery"),
    path("ussd/", UssdCallbackAPIView.as_view(), name="ussd"),

    # ── Router-generated REST routes ──────────────────────────────────────
    path("", include(router.urls)),
]
