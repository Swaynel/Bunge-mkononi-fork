from __future__ import annotations

from collections import Counter

from django.conf import settings
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bill, BillStatus, CountyStat, LogEventType, Petition, PollChoice, PollResponse, Representative, Subscription, SubscriptionChannel, SystemLog
from .serializers import (
    BillSerializer,
    CountyStatSerializer,
    PetitionSerializer,
    PollResponseSerializer,
    RepresentativeSerializer,
    ScrapeTriggerSerializer,
    SubscriptionSerializer,
    SystemLogSerializer,
)
from .services import (
    SMS_DELIVERY_FAILURE_STATUSES,
    SMS_DELIVERY_SUCCESS_STATUSES,
    broadcast_bill_update,
    create_poll_response,
    create_subscription,
    normalize_kenyan_phone_number,
    record_sms_delivery_report,
    record_sms_inbound_message,
    record_system_log,
    sum_log_quantity,
    update_bill_status,
)
from .africastalking import AfricaTalkingConfigurationError, AfricaTalkingError


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


def _serialize_subscription(subscription: Subscription) -> dict:
    return {
        "id": subscription.pk,
        "billId": subscription.bill.pk if subscription.bill else None,
        "billTitle": subscription.bill.title if subscription.bill else None,
        "phoneNumber": subscription.phone_number,
        "channel": subscription.channel,
        "createdAt": subscription.created_at.isoformat(),
    }


def _serialize_sms_inbound_log(log: SystemLog) -> dict:
    metadata = log.metadata if isinstance(log.metadata, dict) else {}
    return {
        "id": log.pk,
        "phoneNumber": metadata.get("phoneNumber") or "",
        "rawPhoneNumber": metadata.get("rawPhoneNumber") or "",
        "message": metadata.get("message") or "",
        "messageId": metadata.get("messageId") or "",
        "linkId": metadata.get("linkId") or "",
        "action": metadata.get("action") or metadata.get("command") or "unknown",
        "billId": metadata.get("billId"),
        "billTitle": metadata.get("billTitle"),
        "created": bool(metadata.get("created")),
        "createdAt": log.created_at.isoformat(),
    }


def _serialize_sms_delivery_log(log: SystemLog) -> dict:
    metadata = log.metadata if isinstance(log.metadata, dict) else {}
    status = str(metadata.get("status") or metadata.get("normalizedStatus") or "unknown")
    return {
        "id": log.pk,
        "messageId": metadata.get("messageId") or "",
        "phoneNumber": metadata.get("phoneNumber") or "",
        "rawPhoneNumber": metadata.get("rawPhoneNumber") or "",
        "status": status,
        "cost": metadata.get("cost") or "",
        "network": metadata.get("network") or "",
        "billId": metadata.get("billId"),
        "billTitle": metadata.get("billTitle"),
        "createdAt": log.created_at.isoformat(),
    }


def _bucket_delivery_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in SMS_DELIVERY_SUCCESS_STATUSES:
        return "delivered"
    if normalized in SMS_DELIVERY_FAILURE_STATUSES:
        return "failed"
    return "pending"


class HealthCheckAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "databaseEngine": settings.DATABASES["default"]["ENGINE"],
                "debug": settings.DEBUG,
                "billCount": Bill.objects.count(),
            }
        )


class DashboardAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        featured_bill = (
            Bill.objects.select_related("petition")
            .prefetch_related("representative_votes__representative", "county_stats", "poll_responses")
            .filter(is_hot=True)
            .first()
            or Bill.objects.select_related("petition")
            .prefetch_related("representative_votes__representative", "county_stats", "poll_responses")
            .first()
        )

        trending_petitions = []
        petitions = Petition.objects.select_related("bill").order_by("-signature_count")[:3]
        for petition in petitions:
            bill = petition.bill
            progress = round((petition.signature_count / petition.goal) * 100, 1) if petition.goal else 0
            trending_petitions.append(
                {
                    "billId": bill.id,
                    "title": petition.title,
                    "signatures": petition.signature_count,
                    "goal": petition.goal,
                    "progressPercent": progress,
                }
            )

        top_county = CountyStat.objects.order_by("-engagement_count", "county").first()

        summary = {
            "activeBills": Bill.objects.exclude(status=BillStatus.PRESIDENTIAL_ASSENT).count(),
            "totalSignatures": Petition.objects.aggregate(total=Sum("signature_count")).get("total") or 0,
            "ussdSessions": sum_log_quantity(LogEventType.USSD_HIT),
            "smsAlertsSent": sum_log_quantity(LogEventType.SMS_BROADCAST),
        }

        return Response(
            {
                "stats": summary,
                "featuredBill": BillSerializer(featured_bill).data if featured_bill else None,
                "trendingPetitions": trending_petitions,
                "topCounty": CountyStatSerializer(top_county).data if top_county else None,
            }
        )


class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [IsStaffOrReadOnly]
    search_fields = ["title", "summary", "category", "status", "sponsor"]
    ordering_fields = ["date_introduced", "title", "subscriber_count", "is_hot"]

    def get_queryset(self):
        queryset = (
            Bill.objects.select_related("petition")
            .prefetch_related("representative_votes__representative", "county_stats", "poll_responses", "subscriptions")
        )

        params = self.request.query_params
        status_filter = params.get("status")
        category = params.get("category")
        hot = params.get("hot")
        search = params.get("search")
        sponsor = params.get("sponsor")
        from_date = params.get("from_date")
        to_date = params.get("to_date")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category:
            queryset = queryset.filter(category=category)
        if hot is not None:
            queryset = queryset.filter(is_hot=hot.lower() in {"1", "true", "yes", "on"})
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(summary__icontains=search)
                | Q(sponsor__icontains=search)
            )
        if sponsor:
            queryset = queryset.filter(sponsor__icontains=sponsor)
        if from_date:
            queryset = queryset.filter(date_introduced__gte=from_date)
        if to_date:
            queryset = queryset.filter(date_introduced__lte=to_date)

        return queryset

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        bill = serializer.save()
        if previous_status != bill.status:
            update_bill_status(bill, bill.status, previous_status=previous_status)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def broadcast(self, request, pk=None):
        bill = self.get_object()
        message = request.data.get("message") or f"Update for {bill.title}: status is now {bill.status}."
        try:
            log = broadcast_bill_update(bill, message)
        except AfricaTalkingConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except AfricaTalkingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(
            {
                "billId": bill.id,
                "subscriberCount": bill.subscriber_count,
                "message": message,
                "logId": log.pk,
            },
            status=status.HTTP_200_OK,
        )


class PetitionViewSet(viewsets.ModelViewSet):
    serializer_class = PetitionSerializer
    permission_classes = [IsStaffOrReadOnly]
    search_fields = ["title", "description"]

    def get_queryset(self):
        queryset = Petition.objects.select_related("bill")
        bill_id = self.request.query_params.get("billId") or self.request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        return queryset


class RepresentativeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RepresentativeSerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["name", "constituency", "county", "party"]

    def get_queryset(self):
        queryset = Representative.objects.prefetch_related("votes__bill")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(constituency__icontains=search)
                | Q(county__icontains=search)
                | Q(party__icontains=search)
            )
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["bill_id"] = self.request.query_params.get("billId") or self.request.query_params.get("bill")
        return context


class CountyStatViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountyStatSerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["county", "sentiment"]

    def get_queryset(self):
        queryset = CountyStat.objects.select_related("bill")
        bill_id = self.request.query_params.get("billId") or self.request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        return queryset


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.select_related("bill")
    search_fields = ["phone_number", "channel"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bill = serializer.validated_data.get("bill")
        phone_number = serializer.validated_data["phone_number"]
        channel = serializer.validated_data.get("channel") or "sms"
        subscription, created = create_subscription(bill, phone_number, channel)
        response_data = SubscriptionSerializer(subscription).data
        response_data["created"] = created
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PollResponseViewSet(viewsets.ModelViewSet):
    serializer_class = PollResponseSerializer
    queryset = PollResponse.objects.select_related("bill")
    search_fields = ["phone_number", "choice"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bill = serializer.validated_data["bill"]
        phone_number = serializer.validated_data.get("phone_number", "")
        choice = serializer.validated_data["choice"]
        response = create_poll_response(bill, phone_number, choice)
        response_data = PollResponseSerializer(response).data
        petition = getattr(bill, "petition", None)
        response_data["petitionSignatureCount"] = petition.signature_count if petition else 0
        return Response(response_data, status=status.HTTP_201_CREATED)


class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ["message", "event_type"]

    def get_queryset(self):
        queryset = SystemLog.objects.all()
        event_type = self.request.query_params.get("eventType") or self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset


@method_decorator(csrf_exempt, name="dispatch")
class SmsInboundAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else request.POST
        result = record_sms_inbound_message(payload)
        bill = result.get("bill")
        response_message = str(result.get("response_message") or "Received.")

        response_payload = {
            "status": "ok",
            "action": result.get("action"),
            "created": bool(result.get("created")),
            "phoneNumber": result.get("phone_number") or "",
            "billId": bill.id if bill else None,
            "billTitle": bill.title if bill else None,
            "message": result.get("message") or "",
            "responseMessage": response_message,
        }
        return HttpResponse(response_payload["responseMessage"], content_type="text/plain")


@method_decorator(csrf_exempt, name="dispatch")
class SmsDeliveryReportAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else request.POST
        result = record_sms_delivery_report(payload)
        status_text = result.get("status") or "unknown"
        return HttpResponse(f"ACK {status_text}", content_type="text/plain")


class AdminMetricsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        inbound_queryset = SystemLog.objects.filter(event_type=LogEventType.SMS_INBOUND)
        delivery_queryset = SystemLog.objects.filter(event_type=LogEventType.SMS_DELIVERY_REPORT)
        sms_inbound_logs = inbound_queryset.order_by("-created_at")[:20]
        delivery_logs = delivery_queryset.order_by("-created_at")[:20]
        subscription_qs = Subscription.objects.select_related("bill").order_by("-created_at")
        top_bills = Bill.objects.order_by("-subscriber_count", "-date_introduced")[:5]

        recent_subscriptions = [_serialize_subscription(subscription) for subscription in subscription_qs[:20]]
        recent_inbound = [_serialize_sms_inbound_log(log) for log in sms_inbound_logs]
        recent_delivery = [_serialize_sms_delivery_log(log) for log in delivery_logs]

        inbound_created_count = sum(
            1
            for metadata in inbound_queryset.values_list("metadata", flat=True)
            if isinstance(metadata, dict) and bool(metadata.get("created"))
        )
        inbound_total = inbound_queryset.count()
        delivery_total = delivery_queryset.count()
        delivery_status_counts = Counter(
            _bucket_delivery_status(
                str(metadata.get("status") or metadata.get("normalizedStatus") or "unknown")
            )
            for metadata in delivery_queryset.values_list("metadata", flat=True)
            if isinstance(metadata, dict)
        )

        return Response(
            {
                "callbackUrls": {
                    "ussd": request.build_absolute_uri(reverse("ussd")),
                    "smsInbound": request.build_absolute_uri(reverse("sms-inbound")),
                    "smsDeliveryReports": request.build_absolute_uri(reverse("sms-delivery")),
                },
                "subscriptionMetrics": {
                    "total": subscription_qs.count(),
                    "sms": subscription_qs.filter(channel=SubscriptionChannel.SMS).count(),
                    "ussd": subscription_qs.filter(channel=SubscriptionChannel.USSD).count(),
                    "recent": recent_subscriptions,
                    "topBills": [
                        {
                            "billId": bill.id,
                            "title": bill.title,
                            "subscriberCount": bill.subscriber_count,
                        }
                        for bill in top_bills
                    ],
                },
                "inboundSms": {
                    "received": inbound_total,
                    "matchedSubscriptions": inbound_created_count,
                    "unmatched": max(inbound_total - inbound_created_count, 0),
                    "recent": recent_inbound,
                },
                "deliveryReports": {
                    "received": delivery_total,
                    "delivered": delivery_status_counts.get("delivered", 0),
                    "failed": delivery_status_counts.get("failed", 0),
                    "pending": delivery_status_counts.get("pending", 0),
                    "recent": recent_delivery,
                },
                "broadcastsSent": sum_log_quantity(LogEventType.SMS_BROADCAST),
                "inboundTotal": inbound_total,
                "deliveryTotal": delivery_total,
            }
        )


class ScrapeBillsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ScrapeTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        timeout = serializer.validated_data["timeout"]

        from .scrapers import scrape_parliament_bills  # noqa: PLC0415

        summary = scrape_parliament_bills(url=url, timeout=timeout)
        processed_bills = summary.get("processed_bills", [])
        processed_summary = ", ".join(
            f"{bill['title']} ({bill['action']})" for bill in processed_bills
        )
        message = (
            "Parliament scrape: "
            f"{summary['bills_found']} found, "
            f"{summary['created']} created, "
            f"{summary['updated']} updated."
        )
        if processed_summary:
            message = f"{message} Processed: {processed_summary}."

        record_system_log(
            LogEventType.SCRAPE,
            message,
            {
                "url": summary["url"],
                "bills_found": summary["bills_found"],
                "pages_fetched": summary.get("pages_fetched", 0),
                "created": summary["created"],
                "updated": summary["updated"],
                "errors": summary["errors"],
                "processedBills": processed_bills,
            },
        )

        return Response(
            {
                "url": summary["url"],
                "billsFound": summary["bills_found"],
                "pagesFetched": summary.get("pages_fetched", 0),
                "created": summary["created"],
                "updated": summary["updated"],
                "errors": summary["errors"],
                "processedBills": [
                    {
                        "billId": bill["bill_id"],
                        "title": bill["title"],
                        "action": bill["action"],
                        "sponsor": bill.get("sponsor", ""),
                    }
                    for bill in processed_bills
                ],
            },
            status=status.HTTP_200_OK if not summary["errors"] else status.HTTP_207_MULTI_STATUS,
        )


class ScrapeHistoryAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        logs = SystemLog.objects.filter(event_type=LogEventType.SCRAPE).order_by("-created_at")[:20]
        return Response(SystemLogSerializer(logs, many=True).data)


class UssdCallbackAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        session_id = request.data.get("sessionId") or request.data.get("session_id") or ""
        phone_number = request.data.get("phoneNumber") or request.data.get("phone_number") or ""
        text = (request.data.get("text") or "").strip()

        record_system_log(
            LogEventType.USSD_HIT,
            "USSD session received.",
            {
                "sessionId": session_id,
                "phoneNumber": phone_number,
                "text": text,
                "quantity": 1,
            },
        )

        featured_bill = Bill.objects.filter(is_hot=True).select_related("petition").first() or Bill.objects.select_related("petition").first()

        if not text:
            return HttpResponse(
                "CON Bunge Mkononi\n"
                "1. View active bills\n"
                "2. Subscribe to a bill\n"
                "3. Vote on the featured bill",
                content_type="text/plain",
            )

        parts = text.split("*")
        choice = parts[0]

        if choice == "1":
            if len(parts) == 1:
                active_bills = Bill.objects.exclude(status=BillStatus.PRESIDENTIAL_ASSENT)[:5]
                lines = [f"{index + 1}. {bill.id} - {bill.title}" for index, bill in enumerate(active_bills)]
                if not lines:
                    return HttpResponse("END No active bills found.", content_type="text/plain")
                return HttpResponse(
                    "CON Active bills\n" + "\n".join(lines) + "\nReply with 1*<billId> for details",
                    content_type="text/plain",
                )

            bill_id = parts[1]
            bill = Bill.objects.select_related("petition").filter(pk=bill_id).first()
            if not bill:
                return HttpResponse("END Bill not found.", content_type="text/plain")

            petition = getattr(bill, "petition", None)
            signatures = petition.signature_count if petition else 0
            return HttpResponse(
                f"END {bill.title}\nStatus: {bill.status}\nSignatures: {signatures}",
                content_type="text/plain",
            )

        if choice == "2":
            if len(parts) == 1:
                active_bills = Bill.objects.exclude(status=BillStatus.PRESIDENTIAL_ASSENT)[:5]
                lines = [f"{index + 1}. {bill.id} - {bill.title}" for index, bill in enumerate(active_bills)]
                return HttpResponse(
                    "CON Subscribe to which bill?\n" + "\n".join(lines) + "\nReply with 2*<billId>",
                    content_type="text/plain",
                )

            bill_id = parts[1]
            bill = Bill.objects.filter(pk=bill_id).first()
            if not bill:
                return HttpResponse("END Bill not found.", content_type="text/plain")

            create_subscription(bill, phone_number, "ussd")
            return HttpResponse(f"END You are now subscribed to {bill.title}.", content_type="text/plain")

        if choice == "3":
            if not featured_bill:
                return HttpResponse("END No featured bill available right now.", content_type="text/plain")

            if len(parts) == 1:
                return HttpResponse(
                    "CON Vote on the featured bill\n1. Support\n2. Oppose\n3. Need more info",
                    content_type="text/plain",
                )

            vote_choice_map = {
                "1": PollChoice.SUPPORT,
                "2": PollChoice.OPPOSE,
                "3": PollChoice.MORE_INFO,
            }
            vote_choice = vote_choice_map.get(parts[1])
            if vote_choice is None:
                return HttpResponse("END Invalid vote option.", content_type="text/plain")

            create_poll_response(featured_bill, phone_number, vote_choice)
            return HttpResponse("END Your vote has been recorded. Thank you.", content_type="text/plain")

        return HttpResponse("END Invalid option.", content_type="text/plain")
