# ============================================================================
# INTEGRATION PATCH
# ============================================================================
#
# This file describes the exact, minimal changes needed to wire the
# Leaders / Voting API into the existing views.py and serializers.py.
# Everything else (new files, urls.py) is a full replacement.
#
# ============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. serializers.py  — append at the bottom of the file
# ─────────────────────────────────────────────────────────────────────────────

SERIALIZERS_APPEND = '''

# ---------------------------------------------------------------------------
# Leaders / Voting API — scrape trigger serializers
# ---------------------------------------------------------------------------

class ScrapeRepresentativesTriggerSerializer(serializers.Serializer):
    """Input for POST /api/scrape/representatives/"""
    role = serializers.ChoiceField(
        choices=["MP", "Senator", "all"],
        default="all",
        help_text="Which role to scrape: MP, Senator, or all.",
    )
    url = serializers.URLField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Override the default parliament members page URL.",
    )
    timeout = serializers.IntegerField(
        required=False, default=30, min_value=5, max_value=120,
    )


class ScrapeVotesTriggerSerializer(serializers.Serializer):
    """Input for POST /api/scrape/votes/"""
    bill_id = serializers.CharField(
        help_text="Bill.id to associate vote records with.",
    )
    url = serializers.URLField(
        help_text="URL of the Hansard division page.",
    )
    timeout = serializers.IntegerField(
        required=False, default=30, min_value=5, max_value=120,
    )
'''


# ─────────────────────────────────────────────────────────────────────────────
# 2. views.py — two things to do:
#
#   a) Add four new imports at the top of the imports block:
#      from collections import defaultdict          ← already there as Counter
#      (already imported: permissions, status, Response, APIView, Bill,
#       LogEventType, RepresentativeVote, cast, record_system_log)
#
#   Specifically add these two serializer imports to the existing
#   `from .serializers import (...)` block:
#
#       ScrapeRepresentativesTriggerSerializer,
#       ScrapeVotesTriggerSerializer,
#
#   b) Append the four new view classes at the bottom of the file
#      (copy the full content of views_additions.py)
# ─────────────────────────────────────────────────────────────────────────────

VIEWS_SERIALIZER_IMPORTS_TO_ADD = [
    "ScrapeRepresentativesTriggerSerializer",
    "ScrapeVotesTriggerSerializer",
]

# The four view classes are in views_additions.py — append that file's
# content (excluding the module docstring) to views.py.


# ─────────────────────────────────────────────────────────────────────────────
# 3. urls.py — full replacement
#    Use the urls.py file in this PR. Key additions:
#
#    New imports:
#      BillVotesAPIView, BillVoteSummaryAPIView,
#      ScrapeRepresentativesAPIView, ScrapeVotesAPIView
#
#    New urlpatterns (add BEFORE router.urls include):
#      path("bills/<str:bill_id>/votes/summary/", BillVoteSummaryAPIView...),
#      path("bills/<str:bill_id>/votes/",         BillVotesAPIView...),
#      path("scrape/representatives/",            ScrapeRepresentativesAPIView...),
#      path("scrape/votes/",                      ScrapeVotesAPIView...),
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# COMPLETE FILE LIST FOR THIS PR
# ─────────────────────────────────────────────────────────────────────────────
#
# NEW files (create these):
#   backend/apps/legislative/representative_scrapers.py
#   backend/apps/legislative/management/commands/scrape_representatives.py
#
# MODIFIED files (apply changes above):
#   backend/apps/legislative/serializers.py   ← append SERIALIZERS_APPEND
#   backend/apps/legislative/views.py         ← add imports + append 4 view classes
#   backend/apps/legislative/urls.py          ← full replacement (urls.py)
# ─────────────────────────────────────────────────────────────────────────────
