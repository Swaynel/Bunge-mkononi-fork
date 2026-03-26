from __future__ import annotations

from collections import Counter, defaultdict
from typing import Sequence, cast

from django.conf import settings
from django.db.models import Q, Sum
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import (
    Bill,
    BillCategory,
    BillStatus,
    CountyStat,
    LogEventType,
    MessageLanguage,
    OutboundMessage,
    OutboundMessageStatus,
    OutboundMessageType,
    Petition,
    PollChoice,
    PollResponse,
    Representative,
    RepresentativeVote,
    Subscription,
    SubscriptionChannel,
    SubscriptionFrequency,
    SubscriptionScope,
    SubscriptionSource,
    SubscriptionStatus,
    SystemLog,
    WebhookEventType,
    WebhookReceipt,
    WebhookEventStatus,
)
from .serializers import (
    BillSerializer,
    BillDetailSerializer,
    CountyStatSerializer,
    BillVoteSummarySerializer,
    PetitionSerializer,
    PollResponseSerializer,
    OutboundMessageSerializer,
    PublicSubscriptionManageSerializer,
    RepresentativeSerializer,
    RepresentativeVoteNestedSerializer,
    ScrapeRepresentativesTriggerSerializer,
    ScrapeVotesTriggerSerializer,
    ScrapeTriggerSerializer,
    SubscriptionLookupSerializer,
    SubscriptionSerializer,
    SystemLogSerializer,
    WebhookReceiptSerializer,
)
from .services import (
    SMS_DELIVERY_FAILURE_STATUSES,
    SMS_DELIVERY_SUCCESS_STATUSES,
    _build_bill_document_summary_message,
    _build_bill_keypoints_message,
    _build_bill_search_message,
    _build_bill_status_message,
    _build_bill_timeline_message,
    _build_county_message,
    _build_petition_message,
    _metadata_value,
    _build_sms_help_message,
    _build_subscription_list_message,
    _build_vote_summary_message,
    _preferred_language_for_phone,
    normalize_kenyan_phone_number,
    _translate,
    _subscription_label,
    _subscription_scope_from_reference,
    _subscription_status_message,
    _resolve_bill_from_reference,
    _resolve_subscription_reference,
    _subscription_action_log,
    _update_subscription_state,
    broadcast_bill_update,
    dispatch_pending_outbound_messages,
    create_poll_response,
    create_subscription,
    generate_due_digests,
    record_sms_delivery_report,
    record_sms_inbound_message,
    record_webhook_receipt,
    record_system_log,
    sum_log_quantity,
    update_bill_status,
)
from .africastalking import AfricaTalkingConfigurationError, AfricaTalkingError

USSD_BILL_PAGE_SIZE = 4
USSD_TITLE_LIMIT = 24
USSD_GENERIC_PAGE_SIZE = 4


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):  # pyright: ignore[reportIncompatibleMethodOverride]
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


def _serialize_subscription(subscription: Subscription) -> dict:
    if subscription.scope == SubscriptionScope.BILL and subscription.bill:
        target = subscription.bill.title
    elif subscription.scope == SubscriptionScope.ALL:
        target = "all bills"
    else:
        target = subscription.target_value or subscription.scope
    return {
        "id": subscription.pk,
        "billId": subscription.bill.pk if subscription.bill else None,
        "billTitle": subscription.bill.title if subscription.bill else None,
        "phoneNumber": subscription.phone_number,
        "channel": subscription.channel,
        "scope": subscription.scope,
        "targetValue": subscription.target_value,
        "language": subscription.language,
        "cadence": subscription.cadence,
        "status": subscription.status,
        "target": target,
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
        "statusCode": metadata.get("statusCode") or "",
        "failureReason": metadata.get("failureReason") or "",
        "cost": metadata.get("cost") or "",
        "network": metadata.get("network") or "",
        "billId": metadata.get("billId"),
        "billTitle": metadata.get("billTitle"),
        "createdAt": log.created_at.isoformat(),
    }


def _serialize_outbound_message(message: OutboundMessage) -> dict:
    return {
        "id": message.pk,
        "billId": message.bill_id,
        "subscriptionId": message.subscription_id,
        "recipientPhoneNumber": message.recipient_phone_number,
        "messageType": message.message_type,
        "language": message.language,
        "status": message.status,
        "provider": message.provider,
        "providerMessageId": message.provider_message_id,
        "providerStatus": message.initial_provider_status,
        "providerStatusCode": message.initial_provider_status_code,
        "providerMessage": message.initial_provider_message,
        "deliveryStatus": message.delivery_status,
        "deliveryStatusCode": message.delivery_status_code,
        "dedupeKey": message.dedupe_key,
        "attemptCount": message.attempt_count,
        "scheduledFor": message.scheduled_for.isoformat() if message.scheduled_for else None,
        "sentAt": message.sent_at.isoformat() if message.sent_at else None,
        "lastError": message.last_error,
        "createdAt": message.created_at.isoformat(),
    }


def _serialize_webhook_receipt(receipt: WebhookReceipt) -> dict:
    return {
        "id": receipt.pk,
        "provider": receipt.provider,
        "eventType": receipt.event_type,
        "externalId": receipt.external_id,
        "phoneNumber": receipt.phone_number,
        "status": receipt.status,
        "responseText": receipt.response_text,
        "processedAt": receipt.processed_at.isoformat() if receipt.processed_at else None,
        "createdAt": receipt.created_at.isoformat(),
    }


def _normalize_request_payload(data: object) -> dict:
    if isinstance(data, dict):
        return data
    if hasattr(data, "dict"):
        try:
            return dict(data.dict())
        except TypeError:
            return {}
    if hasattr(data, "items"):
        try:
            return dict(data.items())
        except TypeError:
            return {}
    return {}


def _bucket_delivery_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in SMS_DELIVERY_SUCCESS_STATUSES:
        return "delivered"
    if normalized in SMS_DELIVERY_FAILURE_STATUSES:
        return "failed"
    return "pending"


def _get_featured_bill() -> Bill | None:
    return Bill.objects.filter(is_hot=True).select_related("petition").first() or Bill.objects.select_related("petition").first()


def _get_active_bills(limit: int | None = None) -> list[Bill]:
    queryset = Bill.objects.exclude(status=BillStatus.PRESIDENTIAL_ASSENT).select_related("petition")
    if limit is not None:
        queryset = queryset[:limit]
    return list(queryset)


def _format_ussd_main_menu(language: str = MessageLanguage.EN) -> str:
    return _translate(language, "main_menu")


def _shorten_ussd_text(value: str, limit: int = USSD_TITLE_LIMIT) -> str:
    text = " ".join((value or "").split()).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _paginate_items(items: list[Bill], page: int, page_size: int) -> tuple[list[Bill], int, int]:
    total_pages = max((len(items) + page_size - 1) // page_size, 1)
    current_page = max(1, min(page, total_pages))
    start = (current_page - 1) * page_size
    return items[start : start + page_size], current_page, total_pages


def _paginate_strings(items: list[str], page: int, page_size: int) -> tuple[list[str], int, int]:
    total_pages = max((len(items) + page_size - 1) // page_size, 1)
    current_page = max(1, min(page, total_pages))
    start = (current_page - 1) * page_size
    return items[start : start + page_size], current_page, total_pages


def _format_bill_detail_menu(bill: Bill, language: str = MessageLanguage.EN) -> str:
    petition = getattr(bill, "petition", None)
    signatures = petition.signature_count if petition else 0
    sponsor = bill.sponsor or "N/A"
    introduced = bill.date_introduced.strftime("%d %b %Y")
    return (
        f"CON {_translate(language, 'bill_details_title')}\n"
        f"{_shorten_ussd_text(bill.title)}\n"
        f"Bill ID: {bill.id}\n"
        f"Category: {bill.category}\n"
        f"Status: {bill.status}\n"
        f"Sponsor: {sponsor}\n"
        f"Introduced: {introduced}\n"
        f"Signatures: {signatures}\n"
        "1. Subscribe\n"
        "2. Vote\n"
        "3. Summary\n"
        "4. Key points\n"
        "5. Timeline\n"
        "6. County impact\n"
        "7. Petition\n"
        "0. Main menu"
    )


def _format_bill_summary(bill: Bill, language: str = MessageLanguage.EN) -> str:
    return f"END {_build_bill_document_summary_message(bill, language)}"


def _format_vote_menu(bill: Bill, language: str = MessageLanguage.EN) -> str:
    return (
        f"CON {_translate(language, 'vote_featured_title')}\n"
        f"{_shorten_ussd_text(bill.title)}\n"
        f"Bill ID: {bill.id}\n"
        "1. Support\n"
        "2. Oppose\n"
        "3. Need more info\n"
        "0. Main menu"
    )


def _format_petition_menu(bill: Bill, language: str = MessageLanguage.EN) -> str:
    petition = getattr(bill, "petition", None)
    if petition is None:
        return f"END {_build_petition_message(bill, language)}"

    return (
        f"CON {_translate(language, 'petition_prefix')}: {_shorten_ussd_text(petition.title)}\n"
        f"Bill ID: {bill.id}\n"
        f"Signatures: {petition.signature_count}\n"
        f"Goal: {petition.goal}\n"
        f"1. {_translate(language, 'support_petition')}\n"
        "0. Main menu"
    )


def _format_watchlist_menu(language: str = MessageLanguage.EN) -> str:
    return (
        f"CON {_translate(language, 'watchlists_title')}\n"
        f"1. {_translate(language, 'subscribe_bills_title')}\n"
        "2. Follow by category\n"
        "3. Follow by county\n"
        "4. Follow by sponsor\n"
        "5. Follow all bills\n"
        "6. My subscriptions\n"
        "0. Main menu"
    )


def _format_bill_list_menu(title: str, bills: list[Bill], prompt: str, language: str = MessageLanguage.EN, page: int = 1) -> str:
    page_bills, current_page, total_pages = _paginate_items(bills, page, USSD_BILL_PAGE_SIZE)
    if not page_bills:
        return _translate(language, "no_bills")

    lines = [
        f"{index}. {bill.id} - {_shorten_ussd_text(bill.title)}"
        for index, bill in enumerate(page_bills, start=1)
    ]
    navigation: list[str] = []
    if current_page > 1:
        navigation.append("9. Back")
    if current_page < total_pages:
        navigation.append("8. More")
    navigation.append("0. Main menu")
    page_label = f" ({current_page}/{total_pages})" if total_pages > 1 else ""
    return "CON " + title + page_label + "\n" + "\n".join(lines) + f"\n{prompt}\n" + "\n".join(navigation)


def _format_string_list_menu(
    title: str,
    values: list[str],
    prompt: str,
    language: str = MessageLanguage.EN,
    page: int = 1,
    empty_message: str | None = None,
) -> str:
    if not values:
        return empty_message or _translate(language, "no_bills")

    page_values, current_page, total_pages = _paginate_strings(values, page, USSD_GENERIC_PAGE_SIZE)
    lines = [f"{index}. {value}" for index, value in enumerate(page_values, start=1)]
    navigation: list[str] = []
    if current_page > 1:
        navigation.append("9. Back")
    if current_page < total_pages:
        navigation.append("8. More")
    navigation.append("0. Main menu")
    page_label = f" ({current_page}/{total_pages})" if total_pages > 1 else ""
    return "CON " + title + page_label + "\n" + "\n".join(lines) + f"\n{prompt}\n" + "\n".join(navigation)


def _bill_categories() -> list[str]:
    categories = [category for category in Bill.objects.values_list("category", flat=True).distinct().order_by("category") if str(category).strip()]
    return list(categories)


def _bill_counties() -> list[str]:
    counties = [
        county
        for county in CountyStat.objects.values_list("county", flat=True).distinct().order_by("county")
        if str(county).strip()
    ]
    return list(counties)


def _bill_sponsors() -> list[str]:
    sponsors = [
        sponsor
        for sponsor in Bill.objects.exclude(sponsor="").values_list("sponsor", flat=True).distinct().order_by("sponsor")
        if str(sponsor).strip()
    ]
    return list(sponsors)


def _manageable_subscriptions_for_phone(phone_number: str) -> list[Subscription]:
    return list(
        Subscription.objects.filter(phone_number=phone_number)
        .filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED])
        .select_related("bill")
        .order_by("-created_at")
    )


def _resolve_bill_list_selection(parts: Sequence[str], bills: list[Bill]) -> tuple[str, int, Bill | None, list[str]]:
    page = 1
    selection_token: str | None = None
    selection_position = -1

    for position, token in enumerate(parts[1:], start=1):
        if token == "0":
            return ("main_menu", page, None, [])
        if selection_token is None and token == "8":
            page += 1
            continue
        if selection_token is None and token == "9":
            if page == 1:
                return ("main_menu", page, None, [])
            page -= 1
            continue
        selection_token = token
        selection_position = position
        break

    page_bills, current_page, _ = _paginate_items(bills, page, USSD_BILL_PAGE_SIZE)
    if selection_token is None:
        return ("menu", current_page, None, [])

    if not selection_token.isdigit():
        return ("invalid", current_page, None, [])

    index = int(selection_token) - 1
    if index < 0 or index >= len(page_bills):
        return ("invalid", current_page, None, [])

    return ("selected", current_page, page_bills[index], list(parts[selection_position + 1 :]))


def _resolve_string_list_selection(parts: Sequence[str], values: list[str]) -> tuple[str, int, str | None, list[str]]:
    page = 1
    selection_token: str | None = None
    selection_position = -1

    for position, token in enumerate(parts[1:], start=1):
        if token == "0":
            return ("main_menu", page, None, [])
        if selection_token is None and token == "8":
            page += 1
            continue
        if selection_token is None and token == "9":
            if page == 1:
                return ("main_menu", page, None, [])
            page -= 1
            continue
        selection_token = token
        selection_position = position
        break

    page_values, current_page, _ = _paginate_strings(values, page, USSD_GENERIC_PAGE_SIZE)
    if selection_token is None:
        return ("menu", current_page, None, [])

    if not selection_token.isdigit():
        return ("invalid", current_page, None, [])

    index = int(selection_token) - 1
    if index < 0 or index >= len(page_values):
        return ("invalid", current_page, None, [])

    return ("selected", current_page, page_values[index], list(parts[selection_position + 1 :]))


def _resolve_subscription_list_selection(
    parts: Sequence[str],
    subscriptions: list[Subscription],
) -> tuple[str, int, Subscription | None, list[str]]:
    page = 1
    selection_token: str | None = None
    selection_position = -1

    for position, token in enumerate(parts[1:], start=1):
        if token == "0":
            return ("main_menu", page, None, [])
        if selection_token is None and token == "8":
            page += 1
            continue
        if selection_token is None and token == "9":
            if page == 1:
                return ("main_menu", page, None, [])
            page -= 1
            continue
        selection_token = token
        selection_position = position
        break

    page_subscriptions, current_page, _ = _paginate_items(cast(list[Bill], subscriptions), page, USSD_GENERIC_PAGE_SIZE)
    if selection_token is None:
        return ("menu", current_page, None, [])

    if not selection_token.isdigit():
        return ("invalid", current_page, None, [])

    index = int(selection_token) - 1
    if index < 0 or index >= len(page_subscriptions):
        return ("invalid", current_page, None, [])

    return ("selected", current_page, page_subscriptions[index], list(parts[selection_position + 1 :]))


def _resolve_vote_choice(choice: str) -> str | None:
    vote_choice_map = {
        "1": PollChoice.SUPPORT,
        "2": PollChoice.OPPOSE,
        "3": PollChoice.MORE_INFO,
    }
    return vote_choice_map.get(choice)


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
    queryset: QuerySet[Bill] = (
        Bill.objects.select_related("petition").prefetch_related(
            "representative_votes__representative",
            "county_stats",
            "poll_responses",
            "subscriptions",
        )
    )
    search_fields = ["id", "title", "summary", "category", "status", "sponsor"]
    ordering_fields = ["date_introduced", "title", "subscriber_count", "is_hot"]

    def get_serializer_class(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        if getattr(self, "action", "") == "retrieve":
            return BillDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet[Bill]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()

        params = request.query_params
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
            search_term = search.strip()
            if search_term:
                queryset = queryset.filter(
                    Q(id__icontains=search_term)
                    | Q(title__icontains=search_term)
                    | Q(summary__icontains=search_term)
                    | Q(category__icontains=search_term)
                    | Q(status__icontains=search_term)
                    | Q(sponsor__icontains=search_term)
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
            actor = getattr(self.request.user, "username", "") or None
            update_bill_status(bill, bill.status, previous_status=previous_status, actor=actor)

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
    queryset: QuerySet[Petition] = Petition.objects.select_related("bill")
    search_fields = ["title", "description"]

    def get_queryset(self) -> QuerySet[Petition]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        bill_id = request.query_params.get("billId") or request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        return queryset


class RepresentativeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RepresentativeSerializer
    permission_classes = [permissions.AllowAny]
    queryset: QuerySet[Representative] = Representative.objects.prefetch_related("votes__bill")
    search_fields = ["name", "constituency", "county", "party"]

    def get_queryset(self) -> QuerySet[Representative]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(constituency__icontains=search)
                | Q(county__icontains=search)
                | Q(party__icontains=search)
            )
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role__iexact=role)
        bill_id = request.query_params.get("billId") or request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(votes__bill_id=bill_id)
            return queryset.distinct()
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = cast(Request, self.request)
        context["bill_id"] = request.query_params.get("billId") or request.query_params.get("bill")
        return context


class CountyStatViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountyStatSerializer
    permission_classes = [permissions.AllowAny]
    queryset: QuerySet[CountyStat] = CountyStat.objects.select_related("bill")
    search_fields = ["county", "sentiment"]

    def get_queryset(self) -> QuerySet[CountyStat]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        bill_id = request.query_params.get("billId") or request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        return queryset


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    queryset: QuerySet[Subscription] = Subscription.objects.select_related("bill")
    search_fields = ["phone_number", "channel"]

    def get_permissions(self):
        if self.action in {"create", "lookup", "manage"}:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, object], serializer.validated_data or {})
        bill = cast(Bill | None, validated_data.get("bill"))
        phone_number = str(validated_data["phone_number"])
        channel = str(validated_data.get("channel") or "sms")
        scope = str(validated_data.get("scope") or SubscriptionScope.BILL)
        target_value = str(validated_data.get("target_value") or "")
        language = validated_data.get("language")
        cadence = str(validated_data.get("cadence") or SubscriptionFrequency.INSTANT)
        status_value = str(validated_data.get("status") or SubscriptionStatus.ACTIVE)

        if bill is None and scope == SubscriptionScope.BILL:
            return Response(
                {"billId": ["This field is required for bill subscriptions."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, created, reactivated = create_subscription(
            bill,
            phone_number,
            channel,
            scope=scope,
            target_value=target_value,
            language=str(language) if language else None,
            cadence=cadence,
            status=status_value,
        )
        response_data = SubscriptionSerializer(subscription).data
        response_data["created"] = created
        response_data["reactivated"] = reactivated
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def lookup(self, request):
        serializer = SubscriptionLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, object], serializer.validated_data or {})
        raw_phone_number = str(validated_data["phone_number"])
        phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number.strip()

        subscriptions = list(
            self.queryset.filter(phone_number=phone_number)
            .exclude(status=SubscriptionStatus.UNSUBSCRIBED)
            .order_by("-created_at")
        )

        return Response(
            {
                "phoneNumber": phone_number,
                "count": len(subscriptions),
                "subscriptions": SubscriptionSerializer(subscriptions, many=True).data,
            }
        )

    @action(detail=True, methods=["post"])
    def manage(self, request, pk=None):
        serializer = PublicSubscriptionManageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, object], serializer.validated_data or {})

        raw_phone_number = str(validated_data["phone_number"])
        phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number.strip()
        subscription = self.get_object()

        if subscription.phone_number != phone_number:
            return Response(
                {"detail": "Phone number does not match this subscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        previous_status = subscription.status
        updated = _update_subscription_state(
            subscription,
            status=str(validated_data["status"]) if "status" in validated_data else None,
            language=str(validated_data["language"]) if "language" in validated_data else None,
            cadence=str(validated_data["cadence"]) if "cadence" in validated_data else None,
            consent_source=SubscriptionSource.API,
        )

        action_name = "update"
        if "status" in validated_data:
            if str(validated_data["status"]) == SubscriptionStatus.PAUSED:
                action_name = "pause"
            elif str(validated_data["status"]) == SubscriptionStatus.ACTIVE:
                action_name = "resume" if previous_status == SubscriptionStatus.PAUSED else "update"
            elif str(validated_data["status"]) == SubscriptionStatus.UNSUBSCRIBED:
                action_name = "unsubscribe"
        elif "language" in validated_data:
            action_name = "language"

        _subscription_action_log(
            action_name,
            phone_number,
            updated,
            {
                "subscriptionId": updated.pk,
                "previousStatus": previous_status,
                "updatedFields": [
                    field_name
                    for field_name in ("status", "language", "cadence")
                    if field_name in validated_data
                ],
            },
        )

        response_data = SubscriptionSerializer(updated).data
        response_data["message"] = _subscription_status_message(updated)
        return Response(response_data)


class PollResponseViewSet(viewsets.ModelViewSet):
    serializer_class = PollResponseSerializer
    queryset: QuerySet[PollResponse] = PollResponse.objects.select_related("bill")
    search_fields = ["phone_number", "choice"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = cast(dict[str, object], serializer.validated_data or {})
        bill = cast(Bill, validated_data["bill"])
        phone_number = str(validated_data.get("phone_number", ""))
        choice = str(validated_data["choice"])
        response = create_poll_response(bill, phone_number, choice)
        response_data = PollResponseSerializer(response).data
        petition = getattr(bill, "petition", None)
        response_data["petitionSignatureCount"] = petition.signature_count if petition else 0
        return Response(response_data, status=status.HTTP_201_CREATED)


class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset: QuerySet[SystemLog] = SystemLog.objects.all()
    search_fields = ["message", "event_type"]

    def get_queryset(self) -> QuerySet[SystemLog]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        event_type = request.query_params.get("eventType") or request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset


class OutboundMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OutboundMessageSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset: QuerySet[OutboundMessage] = OutboundMessage.objects.select_related("bill", "subscription")
    search_fields = ["recipient_phone_number", "message", "message_type", "provider_message_id", "dedupe_key", "last_error"]

    def get_queryset(self) -> QuerySet[OutboundMessage]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        status_filter = request.query_params.get("status")
        message_type = request.query_params.get("messageType") or request.query_params.get("message_type")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if message_type:
            queryset = queryset.filter(message_type=message_type)
        return queryset


class WebhookReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WebhookReceiptSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset: QuerySet[WebhookReceipt] = WebhookReceipt.objects.all()
    search_fields = ["external_id", "phone_number", "raw_phone_number", "event_type", "status"]

    def get_queryset(self) -> QuerySet[WebhookReceipt]:  # pyright: ignore[reportIncompatibleMethodOverride]
        request = cast(Request, self.request)
        queryset = self.queryset.all()
        event_type = request.query_params.get("eventType") or request.query_params.get("event_type")
        status_filter = request.query_params.get("status")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


@method_decorator(csrf_exempt, name="dispatch")
class SmsInboundAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = _normalize_request_payload(request.data if request.data is not None else request.POST)
        raw_phone_number = _metadata_value(payload, "from", "phoneNumber", "phone_number", "msisdn")
        phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number
        message_text = _metadata_value(payload, "text", "message", "smsText", "body")
        message_id = _metadata_value(payload, "id", "messageId", "message_id", "requestId")
        link_id = _metadata_value(payload, "linkId", "link_id")
        external_id = message_id or link_id or f"{phone_number}:{message_text}"

        receipt, created = record_webhook_receipt(
            provider="africastalking",
            event_type=WebhookEventType.SMS_INBOUND,
            external_id=external_id,
            phone_number=phone_number,
            raw_phone_number=raw_phone_number,
            payload=payload,
            status=WebhookEventStatus.PROCESSED,
        )
        if not created and receipt.response_text:
            receipt.status = WebhookEventStatus.DUPLICATE
            receipt.save(update_fields=["status", "updated_at"])
            return HttpResponse(receipt.response_text, content_type="text/plain")

        result = record_sms_inbound_message(payload)
        response_message = str(result.get("response_message") or "Received.")
        receipt.response_text = response_message
        receipt.status = WebhookEventStatus.PROCESSED
        receipt.processed_at = timezone.now()
        receipt.payload = payload
        receipt.save(update_fields=["response_text", "status", "processed_at", "payload", "updated_at"])
        return HttpResponse(response_message, content_type="text/plain")


@method_decorator(csrf_exempt, name="dispatch")
class SmsDeliveryReportAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = _normalize_request_payload(request.data if request.data is not None else request.POST)
        message_id = _metadata_value(payload, "id", "messageId", "message_id", "requestId")
        raw_phone_number = _metadata_value(payload, "phoneNumber", "to", "number", "recipient")
        phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number

        receipt, created = record_webhook_receipt(
            provider="africastalking",
            event_type=WebhookEventType.SMS_DELIVERY_REPORT,
            external_id=message_id or raw_phone_number or phone_number,
            phone_number=phone_number,
            raw_phone_number=raw_phone_number,
            payload=payload,
            status=WebhookEventStatus.PROCESSED,
        )
        if not created and receipt.response_text:
            receipt.status = WebhookEventStatus.DUPLICATE
            receipt.save(update_fields=["status", "updated_at"])
            return HttpResponse(receipt.response_text, content_type="text/plain")

        result = record_sms_delivery_report(payload)
        status_text = result.get("status") or "unknown"
        response_text = f"ACK {status_text}"
        receipt.response_text = response_text
        receipt.status = WebhookEventStatus.PROCESSED
        receipt.processed_at = timezone.now()
        receipt.payload = payload
        receipt.save(update_fields=["response_text", "status", "processed_at", "payload", "updated_at"])
        return HttpResponse(response_text, content_type="text/plain")


class AdminMetricsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        inbound_queryset = SystemLog.objects.filter(event_type=LogEventType.SMS_INBOUND)
        delivery_queryset = SystemLog.objects.filter(event_type=LogEventType.SMS_DELIVERY_REPORT)
        sms_inbound_logs = inbound_queryset.order_by("-created_at")[:20]
        delivery_logs = delivery_queryset.order_by("-created_at")[:20]
        subscription_qs = Subscription.objects.select_related("bill").order_by("-created_at")
        outbound_queryset = OutboundMessage.objects.select_related("bill", "subscription").order_by("-created_at")
        webhook_queryset = WebhookReceipt.objects.order_by("-created_at")
        top_bills = Bill.objects.order_by("-subscriber_count", "-date_introduced")[:5]

        recent_subscriptions = [_serialize_subscription(subscription) for subscription in subscription_qs[:20]]
        recent_inbound = [_serialize_sms_inbound_log(log) for log in sms_inbound_logs]
        recent_delivery = [_serialize_sms_delivery_log(log) for log in delivery_logs]
        recent_outbound = [_serialize_outbound_message(message) for message in outbound_queryset[:20]]
        recent_webhooks = [_serialize_webhook_receipt(receipt) for receipt in webhook_queryset[:20]]

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
        subscription_status_counts = Counter(subscription_qs.values_list("status", flat=True))
        subscription_scope_counts = Counter(subscription_qs.values_list("scope", flat=True))
        subscription_language_counts = Counter(subscription_qs.values_list("language", flat=True))
        subscription_cadence_counts = Counter(subscription_qs.values_list("cadence", flat=True))
        outbound_status_counts = Counter(outbound_queryset.values_list("status", flat=True))
        outbound_type_counts = Counter(outbound_queryset.values_list("message_type", flat=True))
        webhook_status_counts = Counter(webhook_queryset.values_list("status", flat=True))
        webhook_event_counts = Counter(webhook_queryset.values_list("event_type", flat=True))

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
                    "active": subscription_status_counts.get(SubscriptionStatus.ACTIVE, 0),
                    "paused": subscription_status_counts.get(SubscriptionStatus.PAUSED, 0),
                    "unsubscribed": subscription_status_counts.get(SubscriptionStatus.UNSUBSCRIBED, 0),
                    "byStatus": dict(subscription_status_counts),
                    "byScope": dict(subscription_scope_counts),
                    "byLanguage": dict(subscription_language_counts),
                    "byCadence": dict(subscription_cadence_counts),
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
                "messaging": {
                    "outboundMessages": {
                        "total": outbound_queryset.count(),
                        "queued": outbound_status_counts.get(OutboundMessageStatus.QUEUED, 0),
                        "sending": outbound_status_counts.get(OutboundMessageStatus.SENDING, 0),
                        "accepted": outbound_status_counts.get(OutboundMessageStatus.ACCEPTED, 0),
                        "sent": outbound_status_counts.get(OutboundMessageStatus.SENT, 0),
                        "failed": outbound_status_counts.get(OutboundMessageStatus.FAILED, 0),
                        "undelivered": outbound_status_counts.get(OutboundMessageStatus.UNDELIVERED, 0),
                        "skipped": outbound_status_counts.get(OutboundMessageStatus.SKIPPED, 0),
                        "byType": dict(outbound_type_counts),
                        "digestQueue": outbound_type_counts.get(OutboundMessageType.DIGEST, 0),
                        "recent": recent_outbound,
                    },
                    "webhookReceipts": {
                        "total": webhook_queryset.count(),
                        "processed": webhook_status_counts.get(WebhookEventStatus.PROCESSED, 0),
                        "duplicate": webhook_status_counts.get(WebhookEventStatus.DUPLICATE, 0),
                        "failed": webhook_status_counts.get(WebhookEventStatus.FAILED, 0),
                        "ignored": webhook_status_counts.get(WebhookEventStatus.IGNORED, 0),
                        "byEvent": dict(webhook_event_counts),
                        "recent": recent_webhooks,
                    },
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

        validated_data = cast(dict[str, object], serializer.validated_data or {})
        url = str(validated_data.get("url", ""))
        timeout_value = validated_data.get("timeout")
        timeout = timeout_value if isinstance(timeout_value, int) else 30

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
        payload = _normalize_request_payload(request.data if request.data is not None else request.POST)
        session_id = request.data.get("sessionId") or request.data.get("session_id") or ""
        raw_phone_number = request.data.get("phoneNumber") or request.data.get("phone_number") or ""
        phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number
        text = (request.data.get("text") or "").strip()
        external_id = f"{session_id}:{text or 'root'}"

        receipt, created = record_webhook_receipt(
            provider="africastalking",
            event_type=WebhookEventType.USSD,
            external_id=external_id,
            phone_number=phone_number,
            raw_phone_number=raw_phone_number,
            payload=payload,
            status=WebhookEventStatus.PROCESSED,
        )
        if not created and receipt.response_text:
            receipt.status = WebhookEventStatus.DUPLICATE
            receipt.save(update_fields=["status", "updated_at"])
            return HttpResponse(receipt.response_text, content_type="text/plain")

        language = _preferred_language_for_phone(phone_number)
        featured_bill = _get_featured_bill()
        active_bills = _get_active_bills()
        main_menu = _format_ussd_main_menu(language)
        manageable_subscriptions = _manageable_subscriptions_for_phone(phone_number)

        def _store_response(response_text: str) -> HttpResponse:
            receipt.response_text = response_text
            receipt.status = WebhookEventStatus.PROCESSED
            receipt.processed_at = timezone.now()
            receipt.payload = payload
            receipt.save(update_fields=["response_text", "status", "processed_at", "payload", "updated_at"])
            record_system_log(
                LogEventType.USSD_HIT,
                "USSD session processed.",
                {
                    "sessionId": session_id,
                    "phoneNumber": phone_number,
                    "rawPhoneNumber": raw_phone_number,
                    "text": text,
                    "responseText": response_text,
                    "quantity": 1,
                },
            )
            return HttpResponse(response_text, content_type="text/plain")

        def _subscription_confirmation(subscription: Subscription, created_subscription: bool) -> str:
            target_label = _subscription_label(subscription)
            lead = _translate(
                subscription.language,
                "subscribe_confirm" if created_subscription else "already_subscribed",
                bill_title=target_label,
            )
            lines = [lead]
            if subscription.scope == SubscriptionScope.BILL and subscription.bill:
                lines.append(f"Bill ID: {subscription.bill.id}")
            lines.append(_subscription_status_message(subscription))
            lines.append(_translate(subscription.language, "sms_confirmation_pending"))
            return "END " + "\n".join(lines)

        def _subscription_action(subscription: Subscription, action: str) -> str:
            response_key = {
                "pause": "paused",
                "resume": "resumed",
                "unsubscribe": "unsubscribed",
            }[action]
            message = _translate(language, response_key, target=_subscription_label(subscription))
            return "END " + "\n".join([message, _subscription_status_message(subscription)])

        def _handle_bill_detail(bill: Bill, detail_parts: list[str]) -> str:
            if not detail_parts:
                return _format_bill_detail_menu(bill, language)
            if detail_parts[0] == "0":
                return main_menu

            option = detail_parts[0]
            if option == "1":
                subscription, created_subscription, _ = create_subscription(bill, phone_number, "ussd", language=language)
                return _subscription_confirmation(subscription, created_subscription)

            if option == "2":
                if len(detail_parts) == 1:
                    return _format_vote_menu(bill, language)
                if len(detail_parts) == 2:
                    vote_choice = _resolve_vote_choice(detail_parts[1])
                    if vote_choice is None:
                        return _translate(language, "invalid_option")
                    create_poll_response(bill, phone_number, vote_choice)
                    return "END Your vote has been recorded. Thank you."
                return _translate(language, "invalid_option")

            if option == "3":
                return _format_bill_summary(bill, language)

            if option == "4":
                return "END " + _build_bill_keypoints_message(bill, language)

            if option == "5":
                return "END " + _build_bill_timeline_message(bill, language)

            if option == "6":
                return "END " + _build_county_message(bill, language)

            if option == "7":
                if len(detail_parts) == 1:
                    return _format_petition_menu(bill, language)
                if len(detail_parts) == 2 and detail_parts[1] == "1":
                    create_poll_response(bill, phone_number, PollChoice.SUPPORT)
                    return "END " + "\n".join(
                        [
                            _build_petition_message(bill, language),
                            _translate(language, "sms_confirmation_pending"),
                        ]
                    )
                return _translate(language, "invalid_option")

            return _translate(language, "invalid_option")

        def _handle_bill_subscription(parts_for_selection: Sequence[str]) -> str:
            if len(parts_for_selection) == 1:
                return _format_bill_list_menu(
                    _translate(language, "subscribe_bills_title"),
                    active_bills,
                    _translate(language, "reply_subscribe_bill"),
                    language=language,
                )

            route, page, bill, tail = _resolve_bill_list_selection(parts_for_selection, active_bills)
            if route == "main_menu":
                return main_menu
            if route == "menu":
                return _format_bill_list_menu(
                    _translate(language, "subscribe_bills_title"),
                    active_bills,
                    _translate(language, "reply_subscribe_bill"),
                    language=language,
                    page=page,
                )
            if route == "invalid" or bill is None or tail:
                return _translate(language, "invalid_bill")

            subscription, created_subscription, _ = create_subscription(bill, phone_number, "ussd", language=language)
            return _subscription_confirmation(subscription, created_subscription)

        def _handle_scope_subscription(
            scope: str,
            values: list[str],
            title_key: str,
            prompt_key: str,
            parts_for_selection: Sequence[str],
        ) -> str:
            if not parts_for_selection:
                return _format_string_list_menu(
                    _translate(language, title_key),
                    values,
                    _translate(language, prompt_key),
                    language=language,
                )

            pseudo_parts = ["menu", *parts_for_selection]
            route, page, selected_value, tail = _resolve_string_list_selection(pseudo_parts, values)
            if route == "main_menu":
                return main_menu
            if route == "menu":
                return _format_string_list_menu(
                    _translate(language, title_key),
                    values,
                    _translate(language, prompt_key),
                    language=language,
                    page=page,
                )
            if route == "invalid" or selected_value is None or tail:
                return _translate(language, "invalid_option")

            subscription, created_subscription, _ = create_subscription(
                None,
                phone_number,
                "ussd",
                scope=scope,
                target_value=selected_value,
                language=language,
            )
            return _subscription_confirmation(subscription, created_subscription)

        def _handle_manage_subscriptions(parts_for_selection: Sequence[str]) -> str:
            if not manageable_subscriptions:
                return _translate(language, "no_subscriptions")

            if len(parts_for_selection) == 1:
                return _build_subscription_list_message(manageable_subscriptions, language)

            route, page, subscription, tail = _resolve_subscription_list_selection(parts_for_selection, manageable_subscriptions)
            if route == "main_menu":
                return main_menu
            if route == "menu":
                return _build_subscription_list_message(manageable_subscriptions, language)
            if route == "invalid" or subscription is None:
                return _translate(language, "invalid_option")

            if not tail or tail[0] == "0":
                return _translate(language, "manage_menu", target=_subscription_label(subscription))

            action_token = tail[0]
            if action_token == "1":
                updated = _update_subscription_state(subscription, status=SubscriptionStatus.PAUSED)
                _subscription_action_log("pause", phone_number, updated, {"subscriptionId": updated.pk})
                return _subscription_action(updated, "pause")
            if action_token == "2":
                updated = _update_subscription_state(subscription, status=SubscriptionStatus.ACTIVE)
                _subscription_action_log("resume", phone_number, updated, {"subscriptionId": updated.pk})
                return _subscription_action(updated, "resume")
            if action_token == "3":
                updated = _update_subscription_state(subscription, status=SubscriptionStatus.UNSUBSCRIBED)
                _subscription_action_log("unsubscribe", phone_number, updated, {"subscriptionId": updated.pk})
                return _subscription_action(updated, "unsubscribe")

            return _translate(language, "invalid_option")

        if not text:
            return _store_response(main_menu)

        parts = text.split("*")
        choice = parts[0]

        if choice == "0":
            return _store_response(_translate(language, "exit_message"))

        if choice == "1":
            response_text = _format_bill_list_menu(
                _translate(language, "active_bills_title"),
                active_bills,
                _translate(language, "reply_view_bill"),
                language=language,
            )
            if len(parts) > 1:
                route, page, bill, tail = _resolve_bill_list_selection(parts, active_bills)
                if route == "main_menu":
                    response_text = main_menu
                elif route == "menu":
                    response_text = _format_bill_list_menu(
                        _translate(language, "active_bills_title"),
                        active_bills,
                        _translate(language, "reply_view_bill"),
                        language=language,
                        page=page,
                    )
                elif route == "invalid" or bill is None:
                    response_text = _translate(language, "invalid_bill")
                else:
                    response_text = _handle_bill_detail(bill, tail)
            return _store_response(response_text)

        if choice == "2":
            if not featured_bill:
                return _store_response(_translate(language, "no_featured"))
            response_text = _format_bill_detail_menu(featured_bill, language)
            if len(parts) > 1:
                response_text = _handle_bill_detail(featured_bill, parts[1:])
            return _store_response(response_text)

        if choice == "3":
            if len(parts) == 1:
                return _store_response(_format_watchlist_menu(language))
            subchoice = parts[1]
            if subchoice == "0":
                return _store_response(main_menu)
            if subchoice == "1":
                return _store_response(_handle_bill_subscription(parts[1:]))
            if subchoice == "2":
                return _store_response(
                    _handle_scope_subscription(
                        SubscriptionScope.CATEGORY,
                        _bill_categories(),
                        "categories_title",
                        "reply_subscribe_category",
                        parts[2:],
                    )
                )
            if subchoice == "3":
                return _store_response(
                    _handle_scope_subscription(
                        SubscriptionScope.COUNTY,
                        _bill_counties(),
                        "counties_title",
                        "reply_subscribe_county",
                        parts[2:],
                    )
                )
            if subchoice == "4":
                return _store_response(
                    _handle_scope_subscription(
                        SubscriptionScope.SPONSOR,
                        _bill_sponsors(),
                        "sponsors_title",
                        "reply_subscribe_sponsor",
                        parts[2:],
                    )
                )
            if subchoice == "5":
                subscription, created_subscription, _ = create_subscription(
                    None,
                    phone_number,
                    "ussd",
                    scope=SubscriptionScope.ALL,
                    target_value="",
                    language=language,
                )
                return _store_response(_subscription_confirmation(subscription, created_subscription))
            if subchoice == "6":
                return _store_response(_handle_manage_subscriptions(parts[1:]))
            return _store_response(_translate(language, "invalid_option"))

        if choice == "4":
            if not featured_bill:
                return _store_response(_translate(language, "no_featured"))
            if len(parts) == 1:
                return _store_response(_format_vote_menu(featured_bill, language))
            if len(parts) != 2:
                return _store_response(_translate(language, "invalid_option"))
            vote_choice = _resolve_vote_choice(parts[1])
            if vote_choice is None:
                return _store_response(_translate(language, "invalid_option"))
            create_poll_response(featured_bill, phone_number, vote_choice)
            return _store_response("END Your vote has been recorded. Thank you.")

        if choice == "5":
            return _store_response("END " + _build_sms_help_message(language))

        if choice == "6":
            if len(parts) == 1:
                return _store_response(_build_language_menu_response(language))

            selected = parts[1].strip().upper()
            if selected == "0":
                return _store_response(main_menu)

            chosen_language = None
            if selected in {"1", "EN", "ENGLISH"}:
                chosen_language = MessageLanguage.EN
            elif selected in {"2", "SW", "SWAHILI", "KISWAHILI"}:
                chosen_language = MessageLanguage.SW

            if chosen_language is None:
                return _store_response(_build_language_menu_response(language))

            if phone_number:
                Subscription.objects.filter(phone_number=phone_number).update(language=chosen_language)

            record_system_log(
                LogEventType.CONSENT,
                f"Language changed to {chosen_language} for {_mask_phone_number(phone_number) or 'unknown number'}.",
                {
                    "sessionId": session_id,
                    "phoneNumber": phone_number,
                    "language": chosen_language,
                    "quantity": 1,
                },
            )
            return _store_response(_format_ussd_main_menu(chosen_language))

        if choice == "7":
            return _store_response(_handle_manage_subscriptions(parts))

        return _store_response(_translate(language, "invalid_option"))


class ScrapeRepresentativesAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ScrapeRepresentativesTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = cast(dict[str, object], serializer.validated_data or {})
        role = str(validated.get("role", "all"))
        url = str(validated.get("url", "") or "")
        timeout_value = validated.get("timeout", 30)
        timeout = int(timeout_value) if isinstance(timeout_value, int) else 30

        from .representative_scrapers import MP_URL, SENATOR_URL, scrape_all, scrape_representatives  # noqa: PLC0415

        if role == "all":
            summary = scrape_all(timeout=timeout)

            record_system_log(
                LogEventType.SCRAPE,
                (
                    "Representative scrape (all): "
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
                    {"id": item["id"], "name": item["name"], "action": item["action"]}
                    for item in summary.get("processed", [])
                ],
                "errors": summary["errors"],
            },
            status=status.HTTP_200_OK if not summary["errors"] else status.HTTP_207_MULTI_STATUS,
        )


class ScrapeVotesAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ScrapeVotesTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = cast(dict[str, object], serializer.validated_data or {})
        bill_id = str(validated["bill_id"])
        url = str(validated["url"])
        timeout_value = validated.get("timeout", 30)
        timeout = int(timeout_value) if isinstance(timeout_value, int) else 30

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


class BillVotesAPIView(APIView):
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
            queryset = queryset.filter(representative__role__iexact=role_filter)

        votes_data = RepresentativeVoteNestedSerializer(queryset, many=True).data
        enriched = []
        for vote_obj, vote_dict in zip(queryset, votes_data):
            representative = vote_obj.representative
            enriched.append(
                {
                    **vote_dict,
                    "representative": {
                        **vote_dict["representative"],
                        "constituency": representative.constituency,
                        "county": representative.county,
                        "party": representative.party,
                        "role": representative.role,
                    },
                }
            )

        return Response(
            {
                "billId": bill.id,
                "billTitle": bill.title,
                "totalVotes": len(enriched),
                "votes": enriched,
            }
        )


class BillVoteSummaryAPIView(APIView):
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
        county_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0, "abstain": 0})
        party_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0, "abstain": 0})

        for vote in votes:
            total += 1
            representative = vote.representative
            county = representative.county or "Unknown"
            party = representative.party or "Independent"

            if vote.vote == "Yes":
                yes += 1
                county_totals[county]["yes"] += 1
                party_totals[party]["yes"] += 1
            elif vote.vote == "No":
                no += 1
                county_totals[county]["no"] += 1
                party_totals[party]["no"] += 1
            else:
                abstain += 1
                county_totals[county]["abstain"] += 1
                party_totals[party]["abstain"] += 1

        def pct(value: int) -> float:
            return round((value / total) * 100, 1) if total else 0.0

        payload = {
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
            "byCounty": [
                {
                    "county": county,
                    "yes": data["yes"],
                    "no": data["no"],
                    "abstain": data["abstain"],
                    "total": data["yes"] + data["no"] + data["abstain"],
                }
                for county, data in sorted(county_totals.items())
            ],
            "byParty": {
                party: {
                    "yes": data["yes"],
                    "no": data["no"],
                    "abstain": data["abstain"],
                    "total": data["yes"] + data["no"] + data["abstain"],
                }
                for party, data in sorted(party_totals.items())
            },
        }

        return Response(BillVoteSummarySerializer(payload).data)
