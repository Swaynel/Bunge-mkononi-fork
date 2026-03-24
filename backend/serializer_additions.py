"""
Additions to backend/apps/legislative/serializers.py

Add these classes after the existing ones. They power:
  GET /api/representatives/                      — paginated leader list
  GET /api/representatives/{id}/                 — leader detail + full vote history
  GET /api/bills/{id}/votes/                     — all votes on a bill
  GET /api/bills/{id}/votes/summary/             — Yes/No/Abstain tally + by-county
  POST /api/scrape/representatives/              — trigger member scrape
  POST /api/scrape/votes/                        — trigger vote scrape for a bill
"""

# ── ScrapeRepresentativesTriggerSerializer ───────────────────────────────────

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
        help_text=(
            "Override the default parliament members page URL. "
            "Leave blank to use the role default."
        ),
    )
    timeout = serializers.IntegerField(
        required=False,
        default=30,
        min_value=5,
        max_value=120,
        help_text="HTTP request timeout in seconds (5–120).",
    )


# ── ScrapeVotesTriggerSerializer ─────────────────────────────────────────────

class ScrapeVotesTriggerSerializer(serializers.Serializer):
    """Input for POST /api/scrape/votes/"""

    bill_id = serializers.CharField(
        help_text="The Bill.id to associate vote records with (e.g. 'finance-bill-2026').",
    )
    url = serializers.URLField(
        help_text="URL of the Hansard division page containing the voting record.",
    )
    timeout = serializers.IntegerField(
        required=False,
        default=30,
        min_value=5,
        max_value=120,
    )


# ── BillVoteSummarySerializer ─────────────────────────────────────────────────

class BillVoteCountyBreakdownSerializer(serializers.Serializer):
    """Per-county vote tally for a bill."""
    county = serializers.CharField()
    yes = serializers.IntegerField()
    no = serializers.IntegerField()
    abstain = serializers.IntegerField()
    total = serializers.IntegerField()


class BillVoteSummarySerializer(serializers.Serializer):
    """
    Aggregate vote summary for a bill.
    Returned by GET /api/bills/{id}/votes/summary/
    """
    billId = serializers.CharField()
    billTitle = serializers.CharField()
    totalVotes = serializers.IntegerField()
    yes = serializers.IntegerField()
    no = serializers.IntegerField()
    abstain = serializers.IntegerField()
    yesPercent = serializers.FloatField()
    noPercent = serializers.FloatField()
    abstainPercent = serializers.FloatField()
    byCounty = BillVoteCountyBreakdownSerializer(many=True)
    byParty = serializers.DictField(child=serializers.DictField(child=serializers.IntegerField()))
