"""
Additions to backend/apps/legislative/views.py

New views to add:

  ScrapeRepresentativesAPIView   POST /api/scrape/representatives/
  ScrapeVotesAPIView             POST /api/scrape/votes/
  BillVotesAPIView               GET  /api/bills/{bill_id}/votes/
  BillVoteSummaryAPIView         GET  /api/bills/{bill_id}/votes/summary/

The existing RepresentativeViewSet already handles:
  GET /api/representatives/          (list, filterable by ?search=, ?billId=)
  GET /api/representatives/{id}/     (detail with recentVotes)

These four new views complete the Leaders / Voting API.

INTEGRATION STEPS
-----------------
1. Copy representative_scrapers.py → backend/apps/legislative/representative_scrapers.py
2. Copy scrape_representatives.py  → backend/apps/legislative/management/commands/scrape_representatives.py
3. Add the serializer classes from serializer_additions.py to the bottom of serializers.py
4. Add the imports and view classes below to views.py
5. Register the new URL patterns in urls.py (see urls_additions.py)
"""

from __future__ import annotations

from collections import defaultdict
from typing import cast

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bill, LogEventType, RepresentativeVote
from .serializers import (
    RepresentativeVoteNestedSerializer,
    ScrapeRepresentativesTriggerSerializer,
    ScrapeVotesTriggerSerializer,
)
from .services import record_system_log


# ---------------------------------------------------------------------------
# Scrape: Representatives
# ---------------------------------------------------------------------------

class ScrapeRepresentativesAPIView(APIView):
    """
    POST /api/scrape/representatives/

    Triggers a live scrape of parliament.go.ke member pages and upserts
    MPs/Senators into the Representative table.

    Admin only.

    Request body (JSON, all optional):
        {
          "role":    "all" | "MP" | "Senator",   // default: "all"
          "url":     "https://...",               // overrides role default
          "timeout": 30
        }

    Response:
        {
          "role": "all",
          "membersFound":  { "MP": 350, "Senator": 67 },
          "created":       { "MP": 12,  "Senator": 3  },
          "updated":       { "MP": 338, "Senator": 64 },
          "pagesFetched":  { "MP": 4,   "Senator": 2  },
          "errors":        []
        }
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        ser = ScrapeRepresentativesTriggerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        validated = cast(dict, ser.validated_data)
        role: str = str(validated.get("role", "all"))
        url: str = str(validated.get("url", "") or "")
        timeout: int = int(validated.get("timeout", 30))

        from .representative_scrapers import (  # noqa: PLC0415
            MP_URL, SENATOR_URL,
            scrape_all, scrape_representatives,
        )

        if role == "all":
            summary = scrape_all(timeout=timeout)

            record_system_log(
                LogEventType.SCRAPE,
                (
                    f"Representative scrape (all): "
                    f"{summary['total_members_found']} found, "
                    f"{summary['total_created']} created, "
                    f"{summary['total_updated']} updated."
                ),
                {
                    "role": "all",
                    "mp": summary["mp"],
                    "senator": summary["senator"],
                },
            )

            return Response(
                {
                    "role": "all",
                    "membersFound": {
                        "MP": summary["mp"]["members_found"],
                        "Senator": summary["senator"]["members_found"],
                    },
                    "created": {
                        "MP": summary["mp"]["created"],
                        "Senator": summary["senator"]["created"],
                    },
                    "updated": {
                        "MP": summary["mp"]["updated"],
                        "Senator": summary["senator"]["updated"],
                    },
                    "pagesFetched": {
                        "MP": summary["mp"]["pages_fetched"],
                        "Senator": summary["senator"]["pages_fetched"],
                    },
                    "errors": summary["total_errors"],
                },
                status=status.HTTP_200_OK if not summary["total_errors"] else status.HTTP_207_MULTI_STATUS,
            )

        # Single role
        target_url = url or (MP_URL if role == "MP" else SENATOR_URL)
        summary = scrape_representatives(url=target_url, role=role, timeout=timeout)

        record_system_log(
            LogEventType.SCRAPE,
            (
                f"Representative scrape ({role}): "
                f"{summary['members_found']} found, "
                f"{summary['created']} created, "
                f"{summary['updated']} updated."
            ),
            {
                "role": role,
                "url": target_url,
                "members_found": summary["members_found"],
                "pages_fetched": summary["pages_fetched"],
                "created": summary["created"],
                "updated": summary["updated"],
                "errors": summary["errors"],
            },
        )

        return Response(
            {
                "role": role,
                "url": target_url,
                "membersFound": summary["members_found"],
                "pagesFetched": summary["pages_fetched"],
                "created": summary["created"],
                "updated": summary["updated"],
                "processed": [
                    {"id": p["id"], "name": p["name"], "action": p["action"]}
                    for p in summary.get("processed", [])
                ],
                "errors": summary["errors"],
            },
            status=status.HTTP_200_OK if not summary["errors"] else status.HTTP_207_MULTI_STATUS,
        )


# ---------------------------------------------------------------------------
# Scrape: Votes
# ---------------------------------------------------------------------------

class ScrapeVotesAPIView(APIView):
    """
    POST /api/scrape/votes/

    Scrapes a Hansard division page and upserts voting records for a specific
    bill, matching vote entries to existing Representative rows by name.

    Admin only.

    Request body (JSON):
        {
          "bill_id": "finance-bill-2026",
          "url":     "https://www.parliament.go.ke/hansard/division/...",
          "timeout": 30
        }

    Response:
        {
          "billId":     "finance-bill-2026",
          "url":        "https://...",
          "votesFound": 350,
          "created":    40,
          "updated":    310,
          "unmatched":  3,
          "errors":     ["No representative found matching 'Hon. X'"],
          "processed":  [{"representative": "...", "bill": "...", "vote": "Yes", "action": "created"}]
        }
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        ser = ScrapeVotesTriggerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        validated = cast(dict, ser.validated_data)
        bill_id: str = str(validated["bill_id"])
        url: str = str(validated["url"])
        timeout: int = int(validated.get("timeout", 30))

        from .representative_scrapers import scrape_representative_votes  # noqa: PLC0415

        summary = scrape_representative_votes(bill_id=bill_id, url=url, timeout=timeout)

        record_system_log(
            LogEventType.SCRAPE,
            (
                f"Vote scrape for '{bill_id}': "
                f"{summary['votes_found']} found, "
                f"{summary['created']} created, "
                f"{summary['updated']} updated, "
                f"{summary.get('unmatched', 0)} unmatched."
            ),
            {
                "bill_id": bill_id,
                "url": url,
                "votes_found": summary["votes_found"],
                "created": summary["created"],
                "updated": summary["updated"],
                "unmatched": summary.get("unmatched", 0),
                "errors": summary["errors"],
            },
        )

        return Response(
            {
                "billId": summary["bill_id"],
                "url": summary["url"],
                "votesFound": summary["votes_found"],
                "created": summary["created"],
                "updated": summary["updated"],
                "unmatched": summary.get("unmatched", 0),
                "errors": summary["errors"],
                "processed": summary.get("processed", []),
            },
            status=status.HTTP_200_OK if not summary["errors"] else status.HTTP_207_MULTI_STATUS,
        )


# ---------------------------------------------------------------------------
# Bill votes list
# ---------------------------------------------------------------------------

class BillVotesAPIView(APIView):
    """
    GET /api/bills/{bill_id}/votes/

    Returns all RepresentativeVote records for a given bill, with full
    representative details (name, constituency, county, party).

    Public.

    Query params:
      ?vote=Yes|No|Abstain    — filter by vote choice
      ?county=Nairobi         — filter by representative county
      ?party=UDA              — filter by representative party
      ?role=MP|Senator        — filter by representative role
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, bill_id: str):
        bill = Bill.objects.filter(pk=bill_id).first()
        if not bill:
            return Response(
                {"detail": f"Bill '{bill_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = (
            RepresentativeVote.objects
            .filter(bill=bill)
            .select_related("representative")
            .order_by("representative__name")
        )

        params = request.query_params
        vote_filter = params.get("vote")
        county_filter = params.get("county")
        party_filter = params.get("party")
        role_filter = params.get("role")

        if vote_filter:
            queryset = queryset.filter(vote=vote_filter)
        if county_filter:
            queryset = queryset.filter(representative__county__icontains=county_filter)
        if party_filter:
            queryset = queryset.filter(representative__party__icontains=party_filter)
        if role_filter:
            queryset = queryset.filter(representative__role=role_filter)

        votes_data = RepresentativeVoteNestedSerializer(queryset, many=True).data

        # Inline representative detail with constituency + county
        enriched = []
        for vote_obj, vote_dict in zip(queryset, votes_data):
            rep = vote_obj.representative
            enriched.append({
                **vote_dict,
                "representative": {
                    **vote_dict["representative"],
                    "constituency": rep.constituency,
                    "county": rep.county,
                    "party": rep.party,
                    "role": rep.role,
                },
            })

        return Response(
            {
                "billId": bill.id,
                "billTitle": bill.title,
                "totalVotes": len(enriched),
                "votes": enriched,
            }
        )


# ---------------------------------------------------------------------------
# Bill vote summary (aggregated)
# ---------------------------------------------------------------------------

class BillVoteSummaryAPIView(APIView):
    """
    GET /api/bills/{bill_id}/votes/summary/

    Returns an aggregated vote summary for a bill:
      - Overall Yes / No / Abstain counts and percentages
      - Breakdown by county
      - Breakdown by party

    Public.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, bill_id: str):
        bill = Bill.objects.filter(pk=bill_id).first()
        if not bill:
            return Response(
                {"detail": f"Bill '{bill_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        votes = (
            RepresentativeVote.objects
            .filter(bill=bill)
            .select_related("representative")
        )

        total = yes = no = abstain = 0
        county_map: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0, "abstain": 0})
        party_map: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0, "abstain": 0})

        for v in votes:
            total += 1
            rep = v.representative
            county = rep.county or "Unknown"
            party = rep.party or "Independent"

            if v.vote == "Yes":
                yes += 1
                county_map[county]["yes"] += 1
                party_map[party]["yes"] += 1
            elif v.vote == "No":
                no += 1
                county_map[county]["no"] += 1
                party_map[party]["no"] += 1
            else:
                abstain += 1
                county_map[county]["abstain"] += 1
                party_map[party]["abstain"] += 1

        def pct(n: int) -> float:
            return round((n / total) * 100, 1) if total else 0.0

        by_county = [
            {
                "county": county,
                "yes": data["yes"],
                "no": data["no"],
                "abstain": data["abstain"],
                "total": data["yes"] + data["no"] + data["abstain"],
            }
            for county, data in sorted(county_map.items())
        ]

        by_party = {
            party: {
                "yes": data["yes"],
                "no": data["no"],
                "abstain": data["abstain"],
                "total": data["yes"] + data["no"] + data["abstain"],
            }
            for party, data in sorted(party_map.items())
        }

        return Response(
            {
                "billId": bill.id,
                "billTitle": bill.title,
                "billStatus": bill.status,
                "totalVotes": total,
                "yes": yes,
                "no": no,
                "abstain": abstain,
                "yesPercent": pct(yes),
                "noPercent": pct(no),
                "abstainPercent": pct(abstain),
                "byCounty": by_county,
                "byParty": by_party,
            }
        )
