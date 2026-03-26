from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify

from .document_processing import PDFDocumentProcessingError, analyze_pdf_document, resolve_bill_pdf_url
from .africastalking import AfricaTalkingConfigurationError, AfricaTalkingError, send_sms, summarize_sms_response
from .models import (
    Bill,
    CountyStat,
    DocumentProcessingStatus,
    LogEventType,
    MessageLanguage,
    OutboundMessage,
    OutboundMessageStatus,
    OutboundMessageType,
    Petition,
    PollChoice,
    PollResponse,
    RepresentativeVote,
    SubscriptionFrequency,
    SubscriptionScope,
    SubscriptionSource,
    SubscriptionStatus,
    Subscription,
    SubscriptionChannel,
    WebhookEventStatus,
    WebhookEventType,
    WebhookReceipt,
    SystemLog,
)


SMS_SUBSCRIPTION_KEYWORDS = {"SUBSCRIBE", "TRACK", "FOLLOW", "JOIN"}
SMS_STATUS_KEYWORDS = {"STATUS", "DETAIL", "DETAILS", "CURRENT"}
SMS_HELP_KEYWORDS = {"HELP", "INFO", "MENU", "START"}
SMS_UNSUBSCRIBE_KEYWORDS = {"STOP", "UNSUBSCRIBE", "CANCEL", "REMOVE"}
SMS_PAUSE_KEYWORDS = {"PAUSE", "MUTE", "SNOOZE"}
SMS_RESUME_KEYWORDS = {"RESUME", "UNPAUSE", "UNMUTE", "WAKE"}
SMS_LANGUAGE_KEYWORDS = {"LANG", "LANGUAGE", "LUGHA"}
SMS_LIST_KEYWORDS = {"LIST", "SUBSCRIPTIONS", "MY", "MINE"}
SMS_DOCUMENT_KEYWORDS = {"SUMMARY", "KEYPOINTS", "IMPACT", "TIMELINE", "DOC", "DOCUMENT"}
SMS_VOTE_KEYWORDS = {"VOTE", "VOTES", "MP", "REP", "REPRESENTATIVE"}
SMS_PETITION_KEYWORDS = {"PETITION", "SIGN", "SUPPORT"}
SMS_SEARCH_KEYWORDS = {"SEARCH", "FIND", "LOOKUP"}
SMS_DELIVERY_SUCCESS_STATUSES = {"success", "delivered"}
SMS_DELIVERY_FAILURE_STATUSES = {"failed", "undelivered", "rejected", "expired", "expired_failed"}

SMS_COMMAND_ALIASES = {
    "SUMMARY": "summary",
    "KEYPOINTS": "keypoints",
    "IMPACT": "impact",
    "TIMELINE": "timeline",
    "DOC": "document",
    "DOCUMENT": "document",
    "VOTE": "votes",
    "VOTES": "votes",
    "MP": "votes",
    "REP": "votes",
    "REPRESENTATIVE": "votes",
    "PETITION": "petition",
    "SIGN": "sign",
    "SUPPORT": "sign",
    "SEARCH": "search",
    "FIND": "search",
    "LOOKUP": "search",
    "LANG": "language",
    "LANGUAGE": "language",
    "LUGHA": "language",
    "LIST": "list",
    "SUBSCRIPTIONS": "list",
    "MY": "list",
    "MINE": "list",
    "PAUSE": "pause",
    "MUTE": "pause",
    "SNOOZE": "pause",
    "RESUME": "resume",
    "UNPAUSE": "resume",
    "UNMUTE": "resume",
    "WAKE": "resume",
    "STOP": "unsubscribe",
    "UNSUBSCRIBE": "unsubscribe",
    "CANCEL": "unsubscribe",
    "REMOVE": "unsubscribe",
    "HELP": "help",
    "INFO": "help",
    "MENU": "help",
    "START": "help",
    "STATUS": "status",
    "DETAIL": "status",
    "DETAILS": "status",
    "CURRENT": "status",
    "SUBSCRIBE": "subscribe",
    "TRACK": "subscribe",
    "FOLLOW": "subscribe",
    "JOIN": "subscribe",
}


LOCALIZED_TEXT: dict[MessageLanguage, dict[str, str]] = {
    MessageLanguage.EN: {
        "main_menu": (
            "CON Bunge Mkononi\n"
            "1. View active bills\n"
            "2. Featured bill details\n"
            "3. Subscribe to a bill\n"
            "4. Vote on featured bill\n"
            "5. Help\n"
            "6. Language\n"
            "7. My subscriptions\n"
            "0. Exit"
        ),
        "active_bills_title": "Active bills",
        "featured_bill_title": "Featured bill",
        "subscribe_bills_title": "Subscribe to a bill",
        "vote_featured_title": "Vote on featured bill",
        "watchlists_title": "Watchlists",
        "categories_title": "Categories",
        "counties_title": "Counties",
        "sponsors_title": "Sponsors",
        "bill_details_title": "Bill details",
        "reply_subscribe_bill": "Reply with 3*1*<number> to subscribe to a bill.",
        "reply_view_bill": "Reply with 1*<number> for details.",
        "reply_subscribe_category": "Reply with 3*2*<number> to follow a category.",
        "reply_subscribe_county": "Reply with 3*3*<number> to follow a county.",
        "reply_subscribe_sponsor": "Reply with 3*4*<number> to follow a sponsor.",
        "reply_subscribe_all": "Reply with 3*5 to follow all bills.",
        "reply_manage_subscription": "Reply with the number to manage a subscription.",
        "sms_confirmation_pending": "An SMS confirmation is on the way.",
        "support_petition": "Support petition",
        "help": (
            "END Bunge Mkononi help\n"
            "TRACK <bill> to subscribe.\n"
            "STATUS <bill> for the latest update.\n"
            "SUMMARY <bill> for a short brief.\n"
            "DOCUMENT <bill> for the full bill summary.\n"
            "SEARCH <term> to find a bill.\n"
            "IMPACT <bill> for county impact.\n"
            "TIMELINE <bill> for the legislative timeline.\n"
            "VOTES <bill> for MP vote results.\n"
            "SIGN <bill> to support a petition.\n"
            "PAUSE, RESUME, LIST, and LANG are also supported."
        ),
        "invalid_option": "END Invalid option. Please try again.",
        "invalid_bill": "END Invalid bill selection. Please try again.",
        "no_featured": "END No featured bill available right now.",
        "no_bills": "END No active bills found right now.",
        "no_subscriptions": "END You do not have any active subscriptions yet.",
        "exit_message": "END Thank you for using Bunge Mkononi.",
        "language_menu": (
            "CON Choose language\n"
            "1. English\n"
            "2. Kiswahili\n"
            "0. Main menu"
        ),
        "language_updated": "Language updated to English.",
        "subscribe_bill": "Reply with 3*<number> to subscribe",
        "subscribe_confirm": "You are now subscribed to {bill_title}.",
        "already_subscribed": "You are already subscribed to {bill_title}.",
        "paused": "You have paused alerts for {target}.",
        "resumed": "You have resumed alerts for {target}.",
        "unsubscribed": "You have unsubscribed from {target}.",
        "status_prefix": "Bill status",
        "summary_prefix": "Summary",
        "vote_prefix": "Vote summary",
        "petition_prefix": "Petition",
        "county_prefix": "County impact",
        "digest_prefix": "Digest",
        "reply_status": "Reply STATUS {bill_id} for the latest bill update.",
        "reply_track": "Reply TRACK {bill_id} to subscribe.",
        "reply_sign": "Reply SIGN {bill_id} to support the petition.",
        "reply_votes": "Reply VOTES {bill_id} for vote results.",
        "track_help": "Send TRACK <bill id or title> to subscribe to a bill.",
        "status_help": "Send STATUS <bill id or title> to check the latest bill update.",
        "summary_help": "Send SUMMARY <bill id or title> for a short brief.",
        "document_help": "Send DOCUMENT <bill id or title> for the full bill summary.",
        "search_help": "Send SEARCH <term> to find matching bills.",
        "impact_help": "Send IMPACT <bill id or title> for county impact information.",
        "timeline_help": "Send TIMELINE <bill id or title> to see the bill timeline.",
        "votes_help": "Send VOTES <bill id or title> for MP vote results.",
        "sign_help": "Send SIGN <bill id or title> to support the petition.",
        "list_help": "Send LIST to see your subscriptions.",
        "language_help": "Send LANG EN or LANG SW to switch languages.",
        "list_title": "My subscriptions",
        "list_item_active": "{index}. {label} ({status})",
        "list_item_paused": "{index}. {label} ({status})",
        "manage_menu": (
            "CON Manage {target}\n"
            "1. Pause\n"
            "2. Resume\n"
            "3. Unsubscribe\n"
            "0. Main menu"
        ),
        "subscription_details": (
            "Subscription details\n"
            "Target: {target}\n"
            "Channel: {channel}\n"
            "Language: {language_code}\n"
            "Cadence: {cadence}\n"
            "Status: {status}"
        ),
        "search_results_title": "Matching bills",
        "search_no_results": "END No bills matched that search.",
        "search_prompt": "Reply with the number to open a bill.",
    },
    MessageLanguage.SW: {
        "main_menu": (
            "CON Bunge Mkononi\n"
            "1. Tazama miswada hai\n"
            "2. Maelezo ya mswada ulioangaziwa\n"
            "3. Jisajili kwa mswada\n"
            "4. Piga kura kwenye mswada ulioangaziwa\n"
            "5. Msaada\n"
            "6. Lugha\n"
            "7. Usajili wangu\n"
            "0. Toka"
        ),
        "active_bills_title": "Miswada hai",
        "featured_bill_title": "Mswada ulioangaziwa",
        "subscribe_bills_title": "Jisajili kwa mswada",
        "vote_featured_title": "Piga kura kwenye mswada ulioangaziwa",
        "watchlists_title": "Orodha za ufuatiliaji",
        "categories_title": "Aina za miswada",
        "counties_title": "Kaunti",
        "sponsors_title": "Wawasilishaji",
        "bill_details_title": "Maelezo ya mswada",
        "reply_subscribe_bill": "Jibu kwa 3*1*<namba> ili kujisajili kwa mswada.",
        "reply_view_bill": "Jibu kwa 1*<namba> kupata maelezo.",
        "reply_subscribe_category": "Jibu kwa 3*2*<namba> ili kufuatilia aina ya mswada.",
        "reply_subscribe_county": "Jibu kwa 3*3*<namba> ili kufuatilia kaunti.",
        "reply_subscribe_sponsor": "Jibu kwa 3*4*<namba> ili kufuatilia mwasilishaji.",
        "reply_subscribe_all": "Jibu kwa 3*5 kufuatilia miswada yote.",
        "reply_manage_subscription": "Jibu kwa namba ili kusimamia usajili.",
        "sms_confirmation_pending": "Ujumbe wa kuthibitisha SMS unakuja.",
        "support_petition": "Saidia ombi",
        "help": (
            "END Msaada wa Bunge Mkononi\n"
            "TUMA TRACK <mswada> kujiandikisha.\n"
            "TUMA STATUS <mswada> kupata taarifa ya sasa.\n"
            "TUMA SUMMARY <mswada> kupata muhtasari.\n"
            "TUMA DOCUMENT <mswada> kuona muhtasari wa mswada.\n"
            "TUMA SEARCH <neno> kutafuta mswada.\n"
            "TUMA IMPACT <mswada> kuona athari za kaunti.\n"
            "TUMA TIMELINE <mswada> kuona ratiba ya mswada.\n"
            "TUMA VOTES <mswada> kuona matokeo ya wabunge.\n"
            "TUMA SIGN <mswada> kuunga mkono ombi.\n"
            "PAUSE, RESUME, LIST, na LANG pia zipo."
        ),
        "invalid_option": "END Chaguo si sahihi. Tafadhali jaribu tena.",
        "invalid_bill": "END Uteuzi wa mswada si sahihi. Tafadhali jaribu tena.",
        "no_featured": "END Hakuna mswada ulioangaziwa kwa sasa.",
        "no_bills": "END Hakuna miswada hai kwa sasa.",
        "no_subscriptions": "END Huna usajili wowote unaoendelea bado.",
        "exit_message": "END Asante kwa kutumia Bunge Mkononi.",
        "language_menu": (
            "CON Chagua lugha\n"
            "1. English\n"
            "2. Kiswahili\n"
            "0. Menyu kuu"
        ),
        "language_updated": "Lugha imewekwa kuwa Kiswahili.",
        "subscribe_bill": "Jibu kwa 3*<namba> ili kujisajili",
        "subscribe_confirm": "Umejisajili kwa {bill_title}.",
        "already_subscribed": "Tayari umejisajili kwa {bill_title}.",
        "paused": "Umesitisha arifa za {target}.",
        "resumed": "Umeanza tena kupokea arifa za {target}.",
        "unsubscribed": "Umeondoa usajili wa {target}.",
        "status_prefix": "Hali ya mswada",
        "summary_prefix": "Muhtasari",
        "vote_prefix": "Matokeo ya kura",
        "petition_prefix": "Ombi",
        "county_prefix": "Athari kwa kaunti",
        "digest_prefix": "Muhtasari wa arifa",
        "reply_status": "Jibu STATUS {bill_id} kupata taarifa ya sasa.",
        "reply_track": "Jibu TRACK {bill_id} kujiandikisha.",
        "reply_sign": "Jibu SIGN {bill_id} kuunga mkono ombi.",
        "reply_votes": "Jibu VOTES {bill_id} kuona matokeo ya kura.",
        "track_help": "TUMA TRACK <namba ya mswada au jina> kujiandikisha kwa mswada.",
        "status_help": "TUMA STATUS <namba ya mswada au jina> kuona taarifa ya sasa.",
        "summary_help": "TUMA SUMMARY <namba ya mswada au jina> kupata muhtasari.",
        "document_help": "TUMA DOCUMENT <namba ya mswada au jina> kuona muhtasari wa mswada.",
        "search_help": "TUMA SEARCH <neno> kutafuta miswada inayofanana.",
        "impact_help": "TUMA IMPACT <namba ya mswada au jina> kuona athari za kaunti.",
        "timeline_help": "TUMA TIMELINE <namba ya mswada au jina> kuona ratiba ya mswada.",
        "votes_help": "TUMA VOTES <namba ya mswada au jina> kuona matokeo ya wabunge.",
        "sign_help": "TUMA SIGN <namba ya mswada au jina> kuunga mkono ombi.",
        "list_help": "TUMA LIST kuona usajili wako.",
        "language_help": "TUMA LANG EN au LANG SW kubadilisha lugha.",
        "list_title": "Usajili wangu",
        "list_item_active": "{index}. {label} ({status})",
        "list_item_paused": "{index}. {label} ({status})",
        "manage_menu": (
            "CON Simamia {target}\n"
            "1. Sitisha\n"
            "2. Endelea\n"
            "3. Ondoa usajili\n"
            "0. Menyu kuu"
        ),
        "subscription_details": (
            "Maelezo ya usajili\n"
            "Lengo: {target}\n"
            "Njia: {channel}\n"
            "Lugha: {language_code}\n"
            "Marudio: {cadence}\n"
            "Hali: {status}"
        ),
        "search_results_title": "Miswada inayofanana",
        "search_no_results": "END Hakuna mswada uliolingana na utafutaji huo.",
        "search_prompt": "Jibu kwa namba ili kufungua mswada.",
    },
}


def _translate(language: str | None, key: str, **kwargs) -> str:
    try:
        normalized = MessageLanguage((language or MessageLanguage.EN).lower())
    except ValueError:
        normalized = MessageLanguage.EN
    template_map = LOCALIZED_TEXT.get(normalized, LOCALIZED_TEXT[MessageLanguage.EN])
    template = template_map.get(key, LOCALIZED_TEXT[MessageLanguage.EN].get(key, key))
    return template.format(**kwargs)


def _mask_phone_number(phone_number: str) -> str:
    digits = re.sub(r"\D", "", phone_number or "")
    if len(digits) <= 4:
        return phone_number or ""
    return f"***{digits[-4:]}"


def _normalized_key(value: str) -> str:
    return slugify(" ".join((value or "").split()))


def _bill_county_stats(bill: Bill) -> list[CountyStat]:
    return list(CountyStat.objects.filter(bill=bill).order_by("-engagement_count", "county"))


def _message_dedupe_key(*parts: str) -> str:
    digest_source = "|".join(str(part or "").strip().lower() for part in parts if part is not None)
    return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()


def _preferred_language_for_phone(phone_number: str) -> str:
    subscription = (
        Subscription.objects.filter(phone_number=phone_number, status=SubscriptionStatus.ACTIVE)
        .order_by("-created_at")
        .only("language")
        .first()
    )
    if subscription and subscription.language:
        return subscription.language
    return MessageLanguage.EN


def _subscription_label(subscription: Subscription) -> str:
    if subscription.scope == SubscriptionScope.BILL:
        bill = subscription.bill
        if bill is not None:
            return bill.title
        return subscription.target_value
    if subscription.scope == SubscriptionScope.ALL:
        return "all bills"
    return subscription.target_value or subscription.scope


def _subscription_matches_bill(subscription: Subscription, bill: Bill) -> bool:
    if subscription.scope == SubscriptionScope.ALL:
        return True
    if subscription.scope == SubscriptionScope.BILL:
        related_bill = subscription.bill
        return related_bill is not None and related_bill.pk == bill.id
    if subscription.scope == SubscriptionScope.CATEGORY:
        return _normalized_key(subscription.target_value) == _normalized_key(bill.category)
    if subscription.scope == SubscriptionScope.SPONSOR:
        return _normalized_key(subscription.target_value) == _normalized_key(bill.sponsor)
    if subscription.scope == SubscriptionScope.COUNTY:
        bill_counties = {
            _normalized_key(str(county_stat.county))
            for county_stat in _bill_county_stats(bill)
            if str(county_stat.county).strip()
        }
        return _normalized_key(subscription.target_value) in bill_counties
    return False


def _subscription_queryset_for_bill(bill: Bill) -> list[Subscription]:
    subscriptions = (
        Subscription.objects.select_related("bill")
        .filter(status=SubscriptionStatus.ACTIVE)
        .exclude(phone_number="")
        .order_by("-created_at")
    )
    matched: list[Subscription] = []
    seen_numbers: set[str] = set()
    for subscription in subscriptions:
        if _subscription_matches_bill(subscription, bill) and subscription.phone_number not in seen_numbers:
            matched.append(subscription)
            seen_numbers.add(subscription.phone_number)
    return matched


def _subscription_display_status(subscription: Subscription) -> str:
    if subscription.status == SubscriptionStatus.PAUSED:
        return "paused"
    if subscription.status == SubscriptionStatus.UNSUBSCRIBED:
        return "unsubscribed"
    return "active"


def _upsert_subscription(
    bill: Bill | None,
    phone_number: str,
    channel: str,
    *,
    scope: str = SubscriptionScope.BILL,
    target_value: str = "",
    language: str | None = None,
    cadence: str = SubscriptionFrequency.INSTANT,
    status: str = SubscriptionStatus.ACTIVE,
    consent_source: str = SubscriptionSource.API,
) -> tuple[Subscription, bool, bool]:
    normalized_phone = normalize_kenyan_phone_number(phone_number) or phone_number.strip()
    normalized_language = language or _preferred_language_for_phone(normalized_phone) or MessageLanguage.EN
    normalized_target = target_value.strip()

    with transaction.atomic():
        subscription = (
            Subscription.objects.select_for_update()
            .filter(
                bill=bill,
                phone_number=normalized_phone,
                channel=channel,
                scope=scope,
                target_value=normalized_target,
            )
            .first()
        )
        created = subscription is None
        previous_status = subscription.status if subscription is not None else None

        if subscription is None:
            subscription = Subscription(
                bill=bill,
                phone_number=normalized_phone,
                channel=channel,
                scope=scope,
                target_value=normalized_target,
            )

        subscription.language = normalized_language
        subscription.cadence = cadence
        subscription.status = status
        subscription.consent_source = consent_source
        subscription.pause_until = None if status != SubscriptionStatus.PAUSED else subscription.pause_until
        subscription.save()

        if bill is not None and scope == SubscriptionScope.BILL:
            if status == SubscriptionStatus.ACTIVE and (created or previous_status == SubscriptionStatus.UNSUBSCRIBED):
                Bill.objects.filter(pk=bill.pk).update(subscriber_count=F("subscriber_count") + 1)
            elif previous_status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED} and status == SubscriptionStatus.UNSUBSCRIBED:
                Bill.objects.filter(pk=bill.pk, subscriber_count__gt=0).update(subscriber_count=F("subscriber_count") - 1)
        reactivated = bool(previous_status == SubscriptionStatus.UNSUBSCRIBED and status == SubscriptionStatus.ACTIVE)
        return subscription, created, reactivated


def _subscription_status_message(subscription: Subscription) -> str:
    return _translate(
        subscription.language,
        "subscription_details",
        target=_subscription_label(subscription),
        channel=subscription.channel.upper(),
        language_code=subscription.language.upper(),
        cadence=subscription.cadence.upper(),
        status=subscription.status.upper(),
    )


def _build_sms_help_message(language: str) -> str:
    return "\n".join(
        [
            _translate(language, "track_help"),
            _translate(language, "status_help"),
            _translate(language, "summary_help"),
            _translate(language, "document_help"),
            _translate(language, "search_help"),
            _translate(language, "impact_help"),
            _translate(language, "timeline_help"),
            _translate(language, "votes_help"),
            _translate(language, "sign_help"),
            _translate(language, "list_help"),
            _translate(language, "language_help"),
        ]
    )


def _build_bill_status_message(bill: Bill, language: str) -> str:
    petition = getattr(bill, "petition", None)
    signatures = petition.signature_count if petition else 0
    summary = _truncate_text(str(bill.summary or ""), 140)
    return (
        f"{_translate(language, 'status_prefix')}: {bill.status}\n"
        f"Bill ID: {bill.id}\n"
        f"Sponsor: {bill.sponsor or 'N/A'}\n"
        f"Supporters: {signatures}\n"
        f"Summary: {summary or 'No summary available.'}\n"
        f"{_translate(language, 'reply_track', bill_id=bill.id)}"
    )


def _build_bill_document_summary_message(bill: Bill, language: str) -> str:
    document_summary = _truncate_text(str(bill.document_text or bill.summary or ""), 220)
    key_points = bill.key_points if isinstance(bill.key_points, list) else []
    lines = [
        f"{_translate(language, 'summary_prefix')}: {bill.title}",
        f"Bill ID: {bill.id}",
        f"Status: {bill.status}",
        f"Category: {bill.category}",
        f"Document status: {bill.document_status}",
        f"Summary: {document_summary or 'No summary available.'}",
    ]
    if key_points:
        lines.append("Key points:")
        for index, item in enumerate(key_points[:3], start=1):
            lines.append(f"{index}. {item}")
    return "\n".join(lines)


def _build_vote_summary_message(bill: Bill, language: str) -> str:
    votes = (
        RepresentativeVote.objects.filter(bill=bill)
        .select_related("representative")
        .order_by("representative__county", "representative__party", "representative__name")
    )
    total = yes = no = abstain = 0
    county_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0, "abstain": 0})
    for vote in votes:
        total += 1
        county = vote.representative.county or "Unknown"
        if vote.vote == "Yes":
            yes += 1
            county_totals[county]["yes"] += 1
        elif vote.vote == "No":
            no += 1
            county_totals[county]["no"] += 1
        else:
            abstain += 1
            county_totals[county]["abstain"] += 1

    def _pct(value: int) -> float:
        return round((value / total) * 100, 1) if total else 0.0

    lines = [
        f"{_translate(language, 'vote_prefix')}: {bill.title}",
        f"Bill ID: {bill.id}",
        f"Yes: {yes} ({_pct(yes)}%)",
        f"No: {no} ({_pct(no)}%)",
        f"Abstain: {abstain} ({_pct(abstain)}%)",
    ]
    if county_totals:
        lines.append("By county:")
        for county, data in list(county_totals.items())[:3]:
            lines.append(f"{county}: {data['yes']} Y / {data['no']} N / {data['abstain']} A")
    return "\n".join(lines)


def _build_petition_message(bill: Bill, language: str) -> str:
    petition = getattr(bill, "petition", None)
    if petition is None:
        return (
            f"{_translate(language, 'petition_prefix')}: {bill.title}\n"
            "No petition is attached to this bill yet."
        )

    progress = round((petition.signature_count / petition.goal) * 100, 1) if petition.goal else 0
    return (
        f"{_translate(language, 'petition_prefix')}: {petition.title}\n"
        f"Bill ID: {bill.id}\n"
        f"Signatures: {petition.signature_count}\n"
        f"Goal: {petition.goal}\n"
        f"Progress: {progress}%\n"
        f"Description: {_truncate_text(petition.description, 160)}"
    )


def _build_county_message(bill: Bill, language: str) -> str:
    county_stats = _bill_county_stats(bill)
    if not county_stats:
        return f"{_translate(language, 'county_prefix')}: {bill.title}\nNo county impact data yet."
    lines = [f"{_translate(language, 'county_prefix')}: {bill.title}"]
    for stat in county_stats[:4]:
        lines.append(f"{stat.county}: {stat.sentiment} ({stat.engagement_count})")
    return "\n".join(lines)


def _build_subscription_list_message(subscriptions: list[Subscription], language: str) -> str:
    if not subscriptions:
        return _translate(language, "no_subscriptions")

    lines = [f"CON {_translate(language, 'list_title')}"]
    for index, subscription in enumerate(subscriptions, start=1):
        label = _subscription_label(subscription)
        lines.append(
            _translate(
                language,
                "list_item_active" if subscription.status == SubscriptionStatus.ACTIVE else "list_item_paused",
                index=index,
                label=label,
                status=subscription.status.upper(),
            )
        )
    lines.append("Reply with the number to manage a subscription.")
    return "\n".join(lines)


def _build_bill_search_message(bills: list[Bill], language: str, query: str) -> str:
    if not bills:
        return _translate(language, "search_no_results")
    lines = [f"CON {_translate(language, 'search_results_title')}"]
    for index, bill in enumerate(bills[:5], start=1):
        lines.append(f"{index}. {bill.id} - {_truncate_text(bill.title, 28)}")
    lines.append(_translate(language, "search_prompt"))
    lines.append(f"Query: {query}")
    return "\n".join(lines)


def _build_bill_keypoints_message(bill: Bill, language: str) -> str:
    key_points = bill.key_points if isinstance(bill.key_points, list) else []
    lines = [
        f"{_translate(language, 'summary_prefix')}: {bill.title}",
        f"Bill ID: {bill.id}",
        f"Status: {bill.status}",
    ]
    if key_points:
        lines.append("Key points:")
        for index, point in enumerate(key_points[:5], start=1):
            lines.append(f"{index}. {point}")
    else:
        lines.append("No key points available.")
    return "\n".join(lines)


def _build_bill_timeline_message(bill: Bill, language: str) -> str:
    timeline = bill.timeline if isinstance(bill.timeline, list) else []
    if not timeline:
        return (
            f"{_translate(language, 'summary_prefix')}: {bill.title}\n"
            "No timeline is available for this bill yet."
        )
    lines = [f"{_translate(language, 'summary_prefix')}: {bill.title}", f"Bill ID: {bill.id}", "Timeline:"]
    for index, item in enumerate(timeline[:5], start=1):
        if isinstance(item, dict):
            label = item.get("label") or item.get("stage") or item.get("title") or "Update"
            detail = item.get("description") or item.get("text") or item.get("date") or ""
            lines.append(f"{index}. {label}: {detail}".strip())
        else:
            lines.append(f"{index}. {item}")
    return "\n".join(lines)


def _build_language_menu_response(current_language: str) -> str:
    if current_language == MessageLanguage.SW:
        return _translate(MessageLanguage.SW, "language_menu")
    return _translate(MessageLanguage.EN, "language_menu")


def _resolve_bill_from_reference(reference: str, phone_number: str | None = None) -> Bill | None:
    candidate = (reference or "").strip()
    if not candidate:
        if phone_number:
            subscription = (
                Subscription.objects.filter(
                    phone_number=phone_number,
                    status=SubscriptionStatus.ACTIVE,
                    scope=SubscriptionScope.BILL,
                )
                .select_related("bill")
                .order_by("-created_at")
                .first()
            )
            if subscription and subscription.bill:
                return subscription.bill
        return Bill.objects.select_related("petition").first()

    prefix, _, remainder = candidate.partition(" ")
    normalized_prefix = prefix.upper().strip()
    if normalized_prefix in {"BILL", "STATUS", "SUMMARY", "KEYPOINTS", "IMPACT", "VOTES", "PETITION", "SIGN", "COUNTY", "REP", "VOTE"}:
        candidate = remainder.strip()

    if not candidate and phone_number:
        subscription = (
            Subscription.objects.filter(
                phone_number=phone_number,
                status=SubscriptionStatus.ACTIVE,
                scope=SubscriptionScope.BILL,
            )
            .select_related("bill")
            .order_by("-created_at")
            .first()
        )
        if subscription and subscription.bill:
            return subscription.bill

    return resolve_bill_reference(candidate)


def _resolve_subscription_reference(phone_number: str, reference: str) -> Subscription | None:
    candidate = (reference or "").strip()
    queryset = Subscription.objects.select_related("bill").filter(phone_number=phone_number)
    if not candidate:
        return queryset.order_by("-created_at").first()

    normalized = candidate.upper().strip()
    if normalized in {"ALL", "ALL BILLS"}:
        return queryset.filter(scope=SubscriptionScope.ALL).order_by("-created_at").first()

    for subscription in queryset.order_by("-created_at"):
        if subscription.scope == SubscriptionScope.BILL and subscription.bill and (
            candidate.lower() == subscription.bill.id.lower()
            or candidate.lower() in subscription.bill.title.lower()
        ):
            return subscription
        if subscription.scope != SubscriptionScope.BILL and _normalized_key(subscription.target_value) == _normalized_key(candidate):
            return subscription

    return None


def _build_subscription_target(scope: str, reference: str, bill: Bill | None = None) -> tuple[Bill | None, str]:
    if scope == SubscriptionScope.BILL:
        return bill, ""
    if scope == SubscriptionScope.ALL:
        return None, ""
    return None, reference.strip()


def _update_subscription_state(
    subscription: Subscription,
    *,
    status: str | None = None,
    language: str | None = None,
    cadence: str | None = None,
    target_value: str | None = None,
    consent_source: str | None = None,
) -> Subscription:
    fields_to_update: list[str] = []
    previous_status = subscription.status
    if status is not None and subscription.status != status:
        subscription.status = status
        fields_to_update.append("status")
        if status != SubscriptionStatus.PAUSED and subscription.pause_until is not None:
            subscription.pause_until = None
            fields_to_update.append("pause_until")
    if language is not None and subscription.language != language:
        subscription.language = language
        fields_to_update.append("language")
    if cadence is not None and subscription.cadence != cadence:
        subscription.cadence = cadence
        fields_to_update.append("cadence")
    if target_value is not None and subscription.target_value != target_value:
        subscription.target_value = target_value
        fields_to_update.append("target_value")
    if consent_source is not None and subscription.consent_source != consent_source:
        subscription.consent_source = consent_source
        fields_to_update.append("consent_source")
    if fields_to_update:
        subscription.save(update_fields=list(dict.fromkeys(fields_to_update + ["updated_at"])))

    bill = subscription.bill
    if bill is not None and subscription.scope == SubscriptionScope.BILL:
        if previous_status == SubscriptionStatus.UNSUBSCRIBED and subscription.status == SubscriptionStatus.ACTIVE:
            Bill.objects.filter(pk=bill.pk).update(subscriber_count=F("subscriber_count") + 1)
        elif previous_status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED} and subscription.status == SubscriptionStatus.UNSUBSCRIBED:
            Bill.objects.filter(pk=bill.pk, subscriber_count__gt=0).update(subscriber_count=F("subscriber_count") - 1)
    return subscription


def _subscription_action_log(action: str, phone_number: str, subscription: Subscription | None, metadata: dict | None = None) -> None:
    payload = dict(metadata or {})
    bill = subscription.bill if subscription is not None else None
    payload.update(
        {
            "phoneNumber": _mask_phone_number(phone_number),
            "billId": bill.pk if bill is not None else payload.get("billId"),
            "scope": subscription.scope if subscription else payload.get("scope"),
            "targetValue": subscription.target_value if subscription else payload.get("targetValue"),
            "channel": subscription.channel if subscription else payload.get("channel"),
            "language": subscription.language if subscription else payload.get("language"),
        }
    )
    record_system_log(
        LogEventType.CONSENT if action in {"subscribe", "pause", "resume", "unsubscribe", "language"} else LogEventType.SUBSCRIPTION,
        f"Subscription {action} for {_mask_phone_number(phone_number)}.",
        payload,
    )


def _build_subscription_target_message(subscription: Subscription, action: str, language: str | None = None) -> str:
    chosen_language = language or subscription.language
    target = _subscription_label(subscription)
    if action == "pause":
        return _translate(chosen_language, "paused", target=target)
    if action == "resume":
        return _translate(chosen_language, "resumed", target=target)
    if action == "unsubscribe":
        return _translate(chosen_language, "unsubscribed", target=target)
    if action == "subscribe":
        return _translate(chosen_language, "subscribe_confirm", bill_title=target)
    if action == "language":
        if chosen_language == MessageLanguage.SW:
            return _translate(chosen_language, "language_updated")
        return _translate(chosen_language, "language_updated")
    return _subscription_status_message(subscription)


def _subscription_scope_from_reference(reference: str) -> tuple[str, str]:
    text = (reference or "").strip()
    if not text:
        return (SubscriptionScope.BILL, "")

    upper = text.upper()
    if upper == "ALL" or upper == "ALL BILLS":
        return (SubscriptionScope.ALL, "")

    scope_prefixes = {
        "CATEGORY": SubscriptionScope.CATEGORY,
        "COUNTY": SubscriptionScope.COUNTY,
        "SPONSOR": SubscriptionScope.SPONSOR,
    }
    prefix, _, remainder = text.partition(" ")
    scope = scope_prefixes.get(prefix.upper())
    if scope:
        return (scope, remainder.strip())
    return (SubscriptionScope.BILL, text)


def _relevant_subscriptions_for_bill(bill: Bill) -> list[Subscription]:
    subscriptions = _subscription_queryset_for_bill(bill)
    if not subscriptions:
        return []
    return subscriptions


def _bill_matches_search_query(bill: Bill, query: str) -> bool:
    search = _normalized_key(query)
    haystacks = [
        bill.id,
        bill.title,
        bill.summary,
        bill.category,
        bill.status,
        bill.sponsor,
        bill.parliament_url,
        bill.document_text,
        " ".join(str(point) for point in bill.key_points or []),
    ]
    if any(search in _normalized_key(str(value)) for value in haystacks if str(value).strip()):
        return True
    county_names = [str(stat.county) for stat in _bill_county_stats(bill)]
    return any(search in _normalized_key(county) for county in county_names)


def _bill_search_results(query: str, limit: int = 5) -> list[Bill]:
    search = (query or "").strip()
    if not search:
        return []
    queryset = Bill.objects.select_related("petition")
    matches: list[Bill] = []
    for bill in queryset:
        if _bill_matches_search_query(bill, search):
            matches.append(bill)
        if len(matches) >= limit:
            break
    return matches


def queue_outbound_message(
    *,
    recipient_phone_number: str,
    message: str,
    message_type: str,
    language: str = MessageLanguage.EN,
    bill: Bill | None = None,
    subscription: Subscription | None = None,
    dedupe_parts: list[str] | tuple[str, ...] | None = None,
    metadata: dict | None = None,
    scheduled_for: datetime | None = None,
    send_immediately: bool = True,
) -> OutboundMessage:
    normalized_phone = normalize_kenyan_phone_number(recipient_phone_number) or recipient_phone_number.strip()
    dedupe_key = _message_dedupe_key(
        message_type,
        normalized_phone,
        bill.id if bill else "",
        str(subscription.pk) if subscription else "",
        message,
        *(dedupe_parts or []),
    )

    outbound, created = OutboundMessage.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "bill": bill,
            "subscription": subscription,
            "recipient_phone_number": normalized_phone,
            "message": message,
            "message_type": message_type,
            "language": language,
            "status": OutboundMessageStatus.QUEUED,
            "provider": "africastalking",
            "metadata": metadata or {},
            "scheduled_for": scheduled_for or timezone.now(),
        },
    )

    if not created:
        outbound.message = message
        outbound.language = language
        outbound.bill = bill
        outbound.subscription = subscription
        outbound.recipient_phone_number = normalized_phone
        outbound.metadata = metadata or outbound.metadata
        outbound.scheduled_for = scheduled_for or outbound.scheduled_for
        outbound.save(
            update_fields=[
                "bill",
                "subscription",
                "recipient_phone_number",
                "message",
                "language",
                "metadata",
                "scheduled_for",
                "updated_at",
            ]
        )

    record_system_log(
        LogEventType.MESSAGE_OUTBOUND,
        f"Queued {message_type} message for {_mask_phone_number(normalized_phone)}.",
        {
            "billId": bill.id if bill else None,
            "subscriptionId": subscription.pk if subscription else None,
            "phoneNumber": _mask_phone_number(normalized_phone),
            "messageType": message_type,
            "language": language,
            "dedupeKey": dedupe_key,
            "quantity": 1,
        },
    )

    if send_immediately:
        transaction.on_commit(lambda: dispatch_outbound_message(outbound.pk))

    return outbound


def _outbound_metadata_snapshot(outbound: OutboundMessage) -> dict[str, object]:
    if isinstance(outbound.metadata, dict):
        return dict(outbound.metadata)
    return {}


def _stringify_provider_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compose_provider_failure_reason(*, status: str, status_code: str, message: str, fallback: str = "") -> str:
    headline = status or message or fallback or "Africa's Talking did not accept the SMS."
    if status_code:
        headline = f"{headline} (status code {status_code})"
    if message and message != status:
        return f"{headline}: {message}"
    return headline


def dispatch_outbound_message(message_id: int | str) -> OutboundMessage | None:
    outbound = OutboundMessage.objects.filter(pk=message_id).select_related("bill", "subscription").first()
    if outbound is None:
        return None
    if outbound.status in {
        OutboundMessageStatus.ACCEPTED,
        OutboundMessageStatus.SENT,
        OutboundMessageStatus.UNDELIVERED,
    }:
        return outbound
    if outbound.scheduled_for and outbound.scheduled_for > timezone.now():
        return outbound

    subscription = outbound.subscription
    bill = outbound.bill

    try:
        outbound.status = OutboundMessageStatus.SENDING
        outbound.attempt_count += 1
        outbound.save(update_fields=["status", "attempt_count", "updated_at"])
        response = send_sms(
            outbound.message,
            [outbound.recipient_phone_number],
            enqueue=True,
        )
        summary = summarize_sms_response(response)
        recipient_details = summary.get("recipients", []) if isinstance(summary.get("recipients", []), list) else []
        first_recipient = recipient_details[0] if recipient_details and isinstance(recipient_details[0], dict) else {}
        provider_message_id = _stringify_provider_value(first_recipient.get("messageId") if isinstance(first_recipient, dict) else "")
        provider_status = _stringify_provider_value(first_recipient.get("status") if isinstance(first_recipient, dict) else "")
        provider_status_code = _stringify_provider_value(first_recipient.get("statusCode") if isinstance(first_recipient, dict) else "")
        provider_message = _stringify_provider_value(summary.get("providerMessage"))
        provider_cost = _stringify_provider_value(first_recipient.get("cost") if isinstance(first_recipient, dict) else "")

        metadata = _outbound_metadata_snapshot(outbound)
        metadata.update(
            {
                "providerMessage": provider_message,
                "providerStatus": provider_status,
                "providerStatusCode": provider_status_code,
                "providerCost": provider_cost,
                "providerRecipients": recipient_details,
            }
        )

        outbound.metadata = metadata
        outbound.provider_message_id = provider_message_id
        successful_count = int(summary.get("successfulCount") or 0)
        accepted_by_provider = provider_status.lower() == "success" or successful_count > 0
        failure_reason = _compose_provider_failure_reason(
            status=provider_status,
            status_code=provider_status_code,
            message=provider_message,
            fallback="Africa's Talking did not return a successful recipient status.",
        )
        outbound.status = OutboundMessageStatus.ACCEPTED if accepted_by_provider else OutboundMessageStatus.FAILED
        outbound.sent_at = timezone.now() if accepted_by_provider else None
        outbound.last_error = "" if accepted_by_provider else failure_reason
        outbound.save(
            update_fields=[
                "metadata",
                "provider_message_id",
                "status",
                "sent_at",
                "last_error",
                "updated_at",
            ]
        )

        if accepted_by_provider and subscription is not None:
            Subscription.objects.filter(pk=subscription.pk).update(last_notified_at=timezone.now())

        log_metadata = {
            "billId": bill.pk if bill is not None else None,
            "subscriptionId": subscription.pk if subscription is not None else None,
            "phoneNumber": _mask_phone_number(outbound.recipient_phone_number),
            "messageType": outbound.message_type,
            "providerMessageId": provider_message_id,
            "providerStatus": provider_status,
            "providerStatusCode": provider_status_code,
            "providerMessage": provider_message,
            "quantity": 1 if accepted_by_provider else 0,
        }
        if accepted_by_provider:
            record_system_log(
                LogEventType.MESSAGE_OUTBOUND,
                f"Africa's Talking accepted {outbound.message_type} message for {_mask_phone_number(outbound.recipient_phone_number)}.",
                log_metadata,
            )
        else:
            record_system_log(
                LogEventType.MESSAGE_OUTBOUND,
                f"Africa's Talking rejected {outbound.message_type} message for {_mask_phone_number(outbound.recipient_phone_number)}: {failure_reason}",
                {
                    **log_metadata,
                    "error": failure_reason,
                },
            )
    except (AfricaTalkingConfigurationError, AfricaTalkingError) as exc:
        outbound.status = OutboundMessageStatus.FAILED
        outbound.last_error = str(exc)
        outbound.save(update_fields=["status", "last_error", "updated_at"])
        record_system_log(
            LogEventType.MESSAGE_OUTBOUND,
            f"Failed to send {outbound.message_type} message: {exc}",
            {
                "billId": bill.pk if bill is not None else None,
                "subscriptionId": subscription.pk if subscription is not None else None,
                "phoneNumber": _mask_phone_number(outbound.recipient_phone_number),
                "messageType": outbound.message_type,
                "error": str(exc),
                "quantity": 0,
            },
        )
    return outbound


def dispatch_pending_outbound_messages(limit: int = 50) -> list[OutboundMessage]:
    due_messages = list(
        OutboundMessage.objects.filter(
            status__in=[OutboundMessageStatus.QUEUED, OutboundMessageStatus.FAILED],
            scheduled_for__lte=timezone.now(),
        )
        .order_by("scheduled_for", "created_at")[:limit]
    )
    for message in due_messages:
        dispatch_outbound_message(message.pk)
    return due_messages


def _record_webhook_receipt(
    *,
    provider: str,
    event_type: str,
    external_id: str,
    phone_number: str = "",
    raw_phone_number: str = "",
    payload: dict | None = None,
    response_text: str = "",
    status: str = WebhookEventStatus.PROCESSED,
) -> tuple[WebhookReceipt, bool]:
    dedupe_key = _message_dedupe_key(provider, event_type, external_id, phone_number, raw_phone_number)
    receipt, created = WebhookReceipt.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "provider": provider,
            "event_type": event_type,
            "external_id": external_id,
            "phone_number": phone_number,
            "raw_phone_number": raw_phone_number,
            "payload": payload or {},
            "response_text": response_text,
            "status": status,
            "processed_at": timezone.now(),
        },
    )
    if not created:
        receipt.payload = payload or receipt.payload
        receipt.response_text = response_text or receipt.response_text
        receipt.status = status
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["payload", "response_text", "status", "processed_at", "updated_at"])
    return receipt, created


def record_webhook_receipt(
    *,
    provider: str,
    event_type: str,
    external_id: str,
    phone_number: str = "",
    raw_phone_number: str = "",
    payload: dict | None = None,
    response_text: str = "",
    status: str = WebhookEventStatus.PROCESSED,
) -> tuple[WebhookReceipt, bool]:
    return _record_webhook_receipt(
        provider=provider,
        event_type=event_type,
        external_id=external_id,
        phone_number=phone_number,
        raw_phone_number=raw_phone_number,
        payload=payload,
        response_text=response_text,
        status=status,
    )


def _active_subscription_queryset(phone_number: str) -> list[Subscription]:
    return list(
        Subscription.objects.filter(phone_number=phone_number)
        .filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED])
        .select_related("bill")
        .order_by("-created_at")
    )


def _build_digest_for_subscription(subscription: Subscription) -> str:
    language = subscription.language or MessageLanguage.EN
    base_queryset = Bill.objects.select_related("petition")

    if subscription.scope == SubscriptionScope.BILL and subscription.bill is not None:
        bills = list(base_queryset.filter(pk=subscription.bill.pk)[:1])
    elif subscription.scope == SubscriptionScope.CATEGORY:
        bills = list(base_queryset.filter(category__iexact=subscription.target_value).order_by("-updated_at")[:3])
    elif subscription.scope == SubscriptionScope.COUNTY:
        county_name = subscription.target_value
        bills = [
            bill
            for bill in base_queryset.order_by("-updated_at")
            if any(
                _normalized_key(stat.county) == _normalized_key(county_name)
                for stat in _bill_county_stats(bill)
            )
        ][:3]
    elif subscription.scope == SubscriptionScope.SPONSOR:
        bills = list(base_queryset.filter(sponsor__icontains=subscription.target_value).order_by("-updated_at")[:3])
    else:
        bills = list(base_queryset.exclude(status="Presidential Assent").order_by("-updated_at")[:3])

    if not bills:
        return (
            f"{_translate(language, 'digest_prefix')}\n"
            "No new bill updates are available for your watchlist."
        )

    lines = [f"{_translate(language, 'digest_prefix')}"]
    for bill in bills[:3]:
        lines.append(f"{bill.id} - {bill.title}")
        lines.append(f"Status: {bill.status}")
        lines.append(f"Summary: {_truncate_text(str(bill.summary or ''), 100)}")
    return "\n".join(lines)


def generate_due_digests() -> list[OutboundMessage]:
    due: list[OutboundMessage] = []
    now = timezone.now()
    subscriptions = (
        Subscription.objects.filter(status=SubscriptionStatus.ACTIVE)
        .exclude(cadence=SubscriptionFrequency.INSTANT)
        .exclude(phone_number="")
        .select_related("bill")
        .order_by("-created_at")
    )
    for subscription in subscriptions:
        if subscription.cadence == SubscriptionFrequency.DAILY:
            interval = timedelta(days=1)
        elif subscription.cadence == SubscriptionFrequency.WEEKLY:
            interval = timedelta(days=7)
        else:
            continue

        last_digest = subscription.last_digest_at or subscription.consented_at or subscription.created_at
        if now - last_digest < interval:
            continue

        message = _build_digest_for_subscription(subscription)
        outbound = queue_outbound_message(
            recipient_phone_number=subscription.phone_number,
            message=message,
            message_type=OutboundMessageType.DIGEST,
            language=subscription.language,
            bill=subscription.bill if subscription.scope == SubscriptionScope.BILL else None,
            subscription=subscription,
            dedupe_parts=[subscription.scope, subscription.target_value, subscription.cadence, str(last_digest.isoformat())],
            metadata={
                "subscriptionId": subscription.pk,
                "scope": subscription.scope,
                "targetValue": subscription.target_value,
                "cadence": subscription.cadence,
            },
            send_immediately=False,
        )
        due.append(outbound)
        subscription.last_digest_at = now
        subscription.save(update_fields=["last_digest_at", "updated_at"])
        record_system_log(
            LogEventType.DIGEST,
            f"Digest queued for {_mask_phone_number(subscription.phone_number)}.",
            {
                "subscriptionId": subscription.pk,
                "phoneNumber": _mask_phone_number(subscription.phone_number),
                "scope": subscription.scope,
                "targetValue": subscription.target_value,
                "cadence": subscription.cadence,
                "quantity": 1,
            },
        )
    return due


def record_system_log(event_type: str, message: str, metadata: dict | None = None) -> SystemLog:
    safe_metadata: dict = {}
    for key, value in (metadata or {}).items():
        normalized_key = str(key).lower()
        if normalized_key in {"phonenumber", "rawphonenumber", "msisdn", "from", "to", "recipient"} and value:
            safe_metadata[key] = _mask_phone_number(str(value))
        else:
            safe_metadata[key] = value
    return SystemLog.objects.create(event_type=event_type, message=message, metadata=safe_metadata)


def _document_state_from_bill(bill: Bill, source_url: str | None = None) -> dict:
    return {
        "status": bill.document_status,
        "method": bill.document_method,
        "sourceUrl": source_url or bill.document_source_url or "",
        "text": bill.document_text,
        "pages": bill.document_pages if isinstance(bill.document_pages, list) else [],
        "pageCount": bill.document_page_count,
        "wordCount": bill.document_word_count,
        "error": bill.document_error,
    }


def _save_bill_document_state(
    bill: Bill,
    payload: dict,
    source_url: str,
    processed_at: datetime | None = None,
) -> Bill:
    bill.document_status = str(payload.get("status") or DocumentProcessingStatus.UNAVAILABLE)
    bill.document_method = str(payload.get("method") or "")
    bill.document_source_url = source_url
    bill.document_text = str(payload.get("text") or "")
    pages = payload.get("pages")
    bill.document_pages = pages if isinstance(pages, list) else []

    try:
        bill.document_page_count = int(payload.get("pageCount") or 0)
    except (TypeError, ValueError):
        bill.document_page_count = 0

    try:
        bill.document_word_count = int(payload.get("wordCount") or 0)
    except (TypeError, ValueError):
        bill.document_word_count = 0

    bill.document_error = str(payload.get("error") or "")
    bill.document_processed_at = processed_at or timezone.now()
    bill.save(
        update_fields=[
            "document_status",
            "document_method",
            "document_source_url",
            "document_text",
            "document_pages",
            "document_error",
            "document_page_count",
            "document_word_count",
            "document_processed_at",
            "updated_at",
        ]
    )
    return bill


def process_bill_document(bill: Bill, force: bool = False) -> dict:
    source_url = resolve_bill_pdf_url(bill.full_text_url, bill.parliament_url)
    if not source_url:
        return _document_state_from_bill(bill)

    if (
        not force
        and bill.document_source_url == source_url
        and bill.document_status in {
            DocumentProcessingStatus.READY,
            DocumentProcessingStatus.NEEDS_OCR,
            DocumentProcessingStatus.FAILED,
        }
        and bill.document_processed_at is not None
    ):
        return _document_state_from_bill(bill, source_url=source_url)

    try:
        result = analyze_pdf_document(source_url)
    except PDFDocumentProcessingError as exc:  # pragma: no cover - defensive wrapper
        result = {
            "status": DocumentProcessingStatus.FAILED,
            "method": "",
            "sourceUrl": source_url,
            "text": "",
            "pages": [],
            "pageCount": 0,
            "wordCount": 0,
            "error": str(exc),
        }

    _save_bill_document_state(bill, result, source_url)
    return result


def _metadata_value(payload: dict | None, *keys: str) -> str:
    if not isinstance(payload, dict):
        return ""

    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_kenyan_phone_number(phone_number: str) -> str:
    digits = re.sub(r"\D", "", phone_number or "")
    if not digits:
        return ""

    if digits.startswith("254"):
        national = digits[3:12]
    elif digits.startswith("0"):
        national = digits[1:10]
    else:
        national = digits[-9:]

    if len(national) != 9:
        return ""

    return f"+254{national}"


def resolve_bill_reference(reference: str) -> Bill | None:
    candidate = reference.strip()
    if not candidate:
        return None

    slug_candidate = slugify(candidate)
    query_candidates = [candidate]
    if slug_candidate and slug_candidate not in query_candidates:
        query_candidates.append(slug_candidate)

    for value in query_candidates:
        bill = Bill.objects.filter(id__iexact=value).first()
        if bill:
            return bill
        bill = Bill.objects.filter(title__iexact=value).first()
        if bill:
            return bill

    if slug_candidate:
        bill = Bill.objects.filter(id__icontains=slug_candidate).first()
        if bill:
            return bill

    return Bill.objects.filter(title__icontains=candidate).first()


def resolve_bill_from_message_id(message_id: str) -> Bill | None:
    message_id = message_id.strip()
    if not message_id:
        return None

    outbound = OutboundMessage.objects.filter(provider_message_id=message_id).select_related("bill").first()
    if outbound and outbound.bill is not None:
        return outbound.bill

    for receipt in WebhookReceipt.objects.filter(event_type=WebhookEventType.SMS_DELIVERY_REPORT).order_by("-created_at"):
        if receipt.external_id == message_id:
            bill_id = str((receipt.payload or {}).get("billId") or "").strip()
            if bill_id:
                return Bill.objects.filter(pk=bill_id).first()

    for metadata in SystemLog.objects.filter(event_type=LogEventType.SMS_BROADCAST).order_by("-created_at").values_list("metadata", flat=True):
        if not isinstance(metadata, dict):
            continue

        bill_id = str(metadata.get("billId") or "").strip()
        if not bill_id:
            continue

        recipient_details = metadata.get("recipientDetails")
        if isinstance(recipient_details, list):
            for recipient in recipient_details:
                if isinstance(recipient, dict) and str(recipient.get("messageId") or "").strip() == message_id:
                    return Bill.objects.filter(pk=bill_id).first()

        message_ids = metadata.get("messageIds")
        if isinstance(message_ids, list) and message_id in {str(value).strip() for value in message_ids}:
            return Bill.objects.filter(pk=bill_id).first()

    return None


def sum_log_quantity(event_type: str) -> int:
    total = 0
    for metadata in SystemLog.objects.filter(event_type=event_type).values_list("metadata", flat=True):
        quantity = 1
        if isinstance(metadata, dict):
            try:
                quantity = int(metadata.get("quantity", 1))
            except (TypeError, ValueError):
                quantity = 1
        total += quantity
    return total


def _truncate_text(value: str, limit: int = 120) -> str:
    text = " ".join((value or "").split()).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _format_bill_sms_summary(bill: Bill) -> str:
    petition = getattr(bill, "petition", None)
    signatures = petition.signature_count if petition else 0
    summary = _truncate_text(str(bill.summary or ""), 120)
    sponsor = bill.sponsor or "N/A"
    lines = [
        f"Status: {bill.status}",
        f"Sponsor: {sponsor}",
        f"Supporters: {signatures}",
        f"Summary: {summary or 'No summary available.'}",
    ]
    return "\n".join(lines)


def _build_status_change_sms_message(bill: Bill, previous_status: str, new_status: str, language: str = MessageLanguage.EN) -> str:
    return (
        f"Update for {bill.title}: {previous_status} -> {new_status}.\n"
        f"{_translate(language, 'reply_status', bill_id=bill.id)}"
    )


def _build_subscription_confirmation_sms(
    subscription: Subscription,
    bill: Bill | None,
    created: bool,
    language: str = MessageLanguage.EN,
) -> str:
    target_label = _subscription_label(subscription)
    lead = (
        _translate(language, "subscribe_confirm", bill_title=target_label)
        if created
        else _translate(language, "already_subscribed", bill_title=target_label)
    )
    lines = [lead, _subscription_status_message(subscription)]
    if bill is not None and subscription.scope == SubscriptionScope.BILL:
        lines.insert(1, f"Bill ID: {bill.id}")
        lines.insert(2, _format_bill_sms_summary(bill))
        lines.append(_translate(language, "reply_status", bill_id=bill.id))
    return "\n".join(lines)


def _queue_subscription_confirmation_sms(
    subscription: Subscription,
    bill: Bill | None,
    created: bool,
    channel: str,
    *,
    reactivated: bool = False,
) -> None:
    if str(channel).strip().lower() != SubscriptionChannel.USSD:
        return

    phone_number = subscription.phone_number.strip()
    if not phone_number:
        return

    message = _build_subscription_confirmation_sms(subscription, bill, created, subscription.language)

    def _queue_confirmation() -> None:
        queue_outbound_message(
            recipient_phone_number=phone_number,
            message=message,
            message_type=OutboundMessageType.CONFIRMATION,
            language=subscription.language,
            bill=bill,
            subscription=subscription,
            dedupe_parts=[
                "confirmation",
                channel,
                str(created),
                str(reactivated),
            ],
            metadata={
                "billId": bill.id if bill else None,
                "channel": channel,
                "created": created,
            },
        )

    transaction.on_commit(_queue_confirmation)


def parse_sms_subscription_command(message: str) -> tuple[str, str]:
    text = (message or "").strip()
    if not text:
        return ("help", "")

    parts = text.split(None, 1)
    command = parts[0].upper()
    remainder = parts[1].strip() if len(parts) > 1 else ""
    action = SMS_COMMAND_ALIASES.get(command)
    if action:
        return (action, remainder)

    if command in SMS_HELP_KEYWORDS:
        return ("help", "")

    if command in SMS_SUBSCRIPTION_KEYWORDS:
        return ("subscribe", remainder)

    return ("subscribe", text)


def record_sms_inbound_message(payload: dict | None) -> dict:
    raw_phone_number = _metadata_value(payload, "from", "phoneNumber", "phone_number", "msisdn")
    phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number
    message_text = _metadata_value(payload, "text", "message", "smsText", "body")
    message_id = _metadata_value(payload, "id", "messageId", "message_id", "requestId")
    link_id = _metadata_value(payload, "linkId", "link_id")
    command, reference = parse_sms_subscription_command(message_text)
    language = _preferred_language_for_phone(phone_number)

    metadata = {
        "phoneNumber": phone_number,
        "rawPhoneNumber": raw_phone_number,
        "message": message_text,
        "messageId": message_id,
        "linkId": link_id,
        "command": command,
        "reference": reference,
        "quantity": 1,
    }

    def _response(action: str, response_message: str, *, bill: Bill | None = None, subscription: Subscription | None = None, created: bool = False) -> dict:
        metadata["action"] = action
        if bill is not None:
            metadata["billId"] = bill.id
            metadata["billTitle"] = bill.title
        if subscription is not None:
            metadata["subscriptionId"] = subscription.pk
            metadata["subscriptionScope"] = subscription.scope
        record_system_log(
            LogEventType.SMS_INBOUND,
            f"SMS inbound {action} from {_mask_phone_number(phone_number) or 'unknown number'}.",
            metadata,
        )
        return {
            "action": action,
            "phone_number": phone_number,
            "message": message_text,
            "response_message": response_message,
            "bill": bill,
            "subscription": subscription,
            "created": created,
        }

    if command == "help":
        return _response("help", _build_sms_help_message(language))

    if command == "list":
        subscriptions = _active_subscription_queryset(phone_number)
        return _response("list", _build_subscription_list_message(subscriptions, language))

    if command == "language":
        candidate = reference.strip().upper()
        if not candidate:
            return _response("language", _build_language_menu_response(language))

        chosen_language = None
        if candidate in {"1", "EN", "ENGLISH"}:
            chosen_language = MessageLanguage.EN
        elif candidate in {"2", "SW", "SWAHILI", "KISWAHILI"}:
            chosen_language = MessageLanguage.SW

        if chosen_language is None:
            return _response("language", _build_language_menu_response(language))

        if phone_number:
            Subscription.objects.filter(phone_number=phone_number).update(language=chosen_language)
        record_system_log(
            LogEventType.CONSENT,
            f"Language changed to {chosen_language} for {_mask_phone_number(phone_number) or 'unknown number'}.",
            {
                "phoneNumber": phone_number,
                "language": chosen_language,
                "quantity": 1,
            },
        )
        return _response("language", _translate(chosen_language, "language_updated"))

    if command in {"pause", "resume", "unsubscribe"}:
        if not phone_number:
            return _response("missing_phone", "We could not read your phone number.")

        if command == "unsubscribe":
            subscriptions = (
                Subscription.objects.filter(phone_number=phone_number)
                .exclude(status=SubscriptionStatus.UNSUBSCRIBED)
                .select_related("bill")
                .order_by("-created_at")
            )
        else:
            subscriptions = (
                Subscription.objects.filter(phone_number=phone_number)
                .filter(status=SubscriptionStatus.PAUSED if command == "resume" else SubscriptionStatus.ACTIVE)
                .select_related("bill")
                .order_by("-created_at")
            )

        if reference:
            specific = _resolve_subscription_reference(phone_number, reference)
            subscriptions = [specific] if specific is not None else []

        subscriptions = [subscription for subscription in subscriptions if subscription is not None]
        if not subscriptions:
            return _response("invalid_subscription", _translate(language, "no_subscriptions"))

        updated_items: list[str] = []
        target_status = {
            "pause": SubscriptionStatus.PAUSED,
            "resume": SubscriptionStatus.ACTIVE,
            "unsubscribe": SubscriptionStatus.UNSUBSCRIBED,
        }[command]

        for subscription in subscriptions:
            _update_subscription_state(
                subscription,
                status=target_status,
                consent_source=SubscriptionSource.SMS,
            )
            updated_items.append(_subscription_label(subscription))

        target_label = ", ".join(updated_items[:3])
        if len(updated_items) > 3:
            target_label += f" (+{len(updated_items) - 3} more)"

        response_key = {
            "pause": "paused",
            "resume": "resumed",
            "unsubscribe": "unsubscribed",
        }[command]
        response_message = _translate(language, response_key, target=target_label or "your subscriptions")
        _subscription_action_log(command, phone_number, subscriptions[0], {"count": len(updated_items)})
        return _response(command, response_message)

    if command == "search":
        bills = _bill_search_results(reference)
        return _response("search", _build_bill_search_message(bills, language, reference))

    if command in {"status", "summary", "document", "keypoints", "impact", "timeline", "votes", "petition", "sign"}:
        bill = _resolve_bill_from_reference(reference, phone_number)
        if bill is None:
            response_message = _translate(language, "invalid_bill")
            return _response("invalid_bill", response_message)

        if command == "status":
            return _response(command, _build_bill_status_message(bill, language), bill=bill)
        if command == "summary":
            return _response(command, _build_bill_document_summary_message(bill, language), bill=bill)
        if command == "document":
            return _response(command, _build_bill_document_summary_message(bill, language), bill=bill)
        if command == "keypoints":
            return _response(command, _build_bill_keypoints_message(bill, language), bill=bill)
        if command == "impact":
            return _response(command, _build_county_message(bill, language), bill=bill)
        if command == "timeline":
            return _response(command, _build_bill_timeline_message(bill, language), bill=bill)
        if command == "votes":
            return _response(command, _build_vote_summary_message(bill, language), bill=bill)
        if command == "petition":
            return _response(command, _build_petition_message(bill, language), bill=bill)
        if command == "sign":
            create_poll_response(bill, phone_number or "", PollChoice.SUPPORT)
            response_message = (
                _build_petition_message(bill, language)
                + "\n"
                + _translate(language, "reply_sign", bill_id=bill.id)
            )
            return _response(command, response_message, bill=bill)

    if command == "subscribe":
        if not phone_number:
            return _response("missing_phone", "We could not read your phone number.")

        scope, target_value = _subscription_scope_from_reference(reference)
        bill = None
        if scope == SubscriptionScope.BILL:
            bill = _resolve_bill_from_reference(target_value or reference, phone_number)
            if bill is None:
                response_message = _translate(language, "invalid_bill")
                return _response("invalid_bill", response_message)
        elif scope == SubscriptionScope.ALL:
            target_value = ""
        elif not target_value:
            return _response("invalid_bill", _translate(language, "invalid_bill"))

        subscription, created, reactivated = _upsert_subscription(
            bill,
            phone_number,
            SubscriptionChannel.SMS,
            scope=scope,
            target_value=target_value,
            language=language,
            cadence=SubscriptionFrequency.INSTANT,
            status=SubscriptionStatus.ACTIVE,
            consent_source=SubscriptionSource.SMS,
        )

        effective_created = created or reactivated
        _subscription_action_log(
            "subscribe",
            phone_number,
            subscription,
            {"created": created, "reactivated": reactivated},
        )
        response_message = _translate(
            subscription.language,
            "subscribe_confirm" if effective_created else "already_subscribed",
            bill_title=_subscription_label(subscription),
        )

        if subscription.scope == SubscriptionScope.BILL and subscription.bill:
            response_message = (
                f"{response_message}\n"
                f"Bill ID: {subscription.bill.id}\n"
                f"{_build_bill_status_message(subscription.bill, subscription.language)}"
            )
        else:
            response_message = (
                f"{response_message}\n"
                f"{_subscription_status_message(subscription)}"
            )

        return _response(
            "subscribe",
            response_message,
            bill=subscription.bill,
            subscription=subscription,
            created=effective_created,
        )

    response_message = _build_sms_help_message(language)
    return _response("help", response_message)


def record_sms_delivery_report(payload: dict | None) -> dict:
    message_id = _metadata_value(payload, "id", "messageId", "message_id", "requestId")
    raw_phone_number = _metadata_value(payload, "phoneNumber", "to", "number", "recipient")
    phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number
    status = _metadata_value(payload, "status", "deliveryStatus", "state") or "unknown"
    status_code = _metadata_value(payload, "statusCode", "deliveryStatusCode", "code")
    failure_reason = _metadata_value(payload, "failureReason", "reason", "description")
    bill = resolve_bill_from_message_id(message_id)
    bill_id = bill.id if bill else ""

    metadata = {
        "messageId": message_id,
        "phoneNumber": phone_number,
        "rawPhoneNumber": raw_phone_number,
        "status": status,
        "normalizedStatus": status.lower(),
        "statusCode": status_code,
        "failureReason": failure_reason,
        "cost": _metadata_value(payload, "cost", "messageCost"),
        "network": _metadata_value(payload, "network", "networkCode"),
        "billId": bill.id if bill else None,
        "billTitle": bill.title if bill else None,
        "quantity": 1,
    }

    _record_webhook_receipt(
        provider="africastalking",
        event_type=WebhookEventType.SMS_DELIVERY_REPORT,
        external_id=message_id or raw_phone_number or phone_number,
        phone_number=phone_number,
        raw_phone_number=raw_phone_number,
        payload={**(payload or {}), "billId": bill_id},
        response_text=status,
        status=WebhookEventStatus.PROCESSED,
    )

    outbound = OutboundMessage.objects.filter(provider_message_id=message_id).first()
    if outbound is not None:
        outbound_metadata = _outbound_metadata_snapshot(outbound)
        outbound_metadata.update(
            {
                "deliveryStatus": status,
                "deliveryStatusCode": status_code,
                "deliveryFailureReason": failure_reason,
                "deliveryCost": metadata["cost"],
                "deliveryNetwork": metadata["network"],
                "deliveryPayload": payload or {},
            }
        )
        outbound.metadata = outbound_metadata
        normalized_status = status.lower()
        update_fields = ["metadata", "updated_at"]
        if normalized_status in SMS_DELIVERY_SUCCESS_STATUSES:
            outbound.status = OutboundMessageStatus.SENT
            outbound.last_error = ""
            update_fields.extend(["status", "last_error"])
        elif normalized_status in SMS_DELIVERY_FAILURE_STATUSES:
            outbound.status = OutboundMessageStatus.UNDELIVERED
            outbound.last_error = _compose_provider_failure_reason(
                status=status,
                status_code=status_code,
                message=failure_reason,
                fallback="Africa's Talking reported the SMS as undelivered.",
            )
            update_fields.extend(["status", "last_error"])
        elif outbound.status not in {OutboundMessageStatus.SENT, OutboundMessageStatus.UNDELIVERED}:
            outbound.status = OutboundMessageStatus.ACCEPTED
            update_fields.append("status")
        outbound.save(update_fields=update_fields)

    record_system_log(
        LogEventType.SMS_DELIVERY_REPORT,
        f"SMS delivery report received for {message_id or 'unknown message'}: {status}.",
        metadata,
    )

    return metadata


def update_bill_status(bill: Bill, new_status: str, actor: str | None = None, previous_status: str | None = None) -> Bill:
    previous_status = previous_status if previous_status is not None else bill.status
    if previous_status == new_status:
        return bill

    if bill.status != new_status:
        bill.status = new_status
        bill.save(update_fields=["status", "updated_at"])

    payload = {
        "billId": bill.id,
        "fromStatus": previous_status,
        "toStatus": new_status,
    }
    if actor:
        payload["actor"] = actor

    record_system_log(
        LogEventType.STATUS_CHANGE,
        f"{bill.title} moved from {previous_status} to {new_status}.",
        payload,
    )

    def _notify_subscribers() -> None:
        try:
            broadcast_bill_update(
                bill,
                _build_status_change_sms_message(bill, previous_status, new_status),
                previous_status=previous_status,
                new_status=new_status,
            )
        except AfricaTalkingError:
            return

    transaction.on_commit(_notify_subscribers)
    return bill


def broadcast_bill_update(
    bill: Bill,
    message: str,
    *,
    previous_status: str | None = None,
    new_status: str | None = None,
) -> SystemLog:
    subscriptions = [
        subscription
        for subscription in _relevant_subscriptions_for_bill(bill)
        if subscription.cadence in {SubscriptionFrequency.INSTANT, SubscriptionFrequency.MILESTONE}
    ]

    if not subscriptions:
        metadata = {
            "billId": bill.id,
            "subscriberCount": bill.subscriber_count,
            "recipientCount": 0,
            "successfulCount": 0,
            "failedCount": 0,
            "quantity": 0,
            "provider": "africastalking",
            "providerMessage": "No SMS subscribers are registered for this bill.",
        }
        return record_system_log(
            LogEventType.SMS_BROADCAST,
            f"No SMS subscribers are registered for {bill.title}.",
            metadata,
        )

    recipient_details: list[dict[str, str]] = []
    message_ids: list[str] = []
    recipient_count = 0
    body = message.strip() if message else ""
    for subscription in subscriptions:
        if not subscription.phone_number.strip():
            continue
        recipient_count += 1
        subscription_message = body or _build_status_change_sms_message(
            bill,
            previous_status or bill.status,
            new_status or bill.status,
            subscription.language,
        )
        outbound = queue_outbound_message(
            recipient_phone_number=subscription.phone_number,
            message=subscription_message,
            message_type=OutboundMessageType.BROADCAST,
            language=subscription.language,
            bill=bill,
            subscription=subscription,
            dedupe_parts=[
                bill.id,
                previous_status or bill.status,
                new_status or bill.status,
                subscription.scope,
                subscription.target_value,
            ],
            metadata={
                "billId": bill.id,
                "subscriptionId": subscription.pk,
                "scope": subscription.scope,
                "targetValue": subscription.target_value,
                "previousStatus": previous_status,
                "newStatus": new_status,
            },
        )
        if outbound.provider_message_id:
            message_ids.append(outbound.provider_message_id)
        recipient_details.append(
            {
                "number": _mask_phone_number(subscription.phone_number),
                "messageId": outbound.provider_message_id,
                "status": outbound.status,
                "scope": subscription.scope,
            }
        )

    delivered_count = recipient_count
    metadata = {
        "billId": bill.id,
        "subscriberCount": bill.subscriber_count,
        "recipientCount": recipient_count,
        "successfulCount": delivered_count,
        "failedCount": 0,
        "quantity": delivered_count,
        "provider": "africastalking",
        "providerMessage": "Queued broadcast messages for matching subscribers.",
        "recipientDetails": recipient_details,
        "messageIds": message_ids,
    }
    return record_system_log(LogEventType.SMS_BROADCAST, message, metadata)


def create_subscription(
    bill: Bill | None,
    phone_number: str,
    channel: str,
    *,
    scope: str = SubscriptionScope.BILL,
    target_value: str = "",
    language: str | None = None,
    cadence: str = SubscriptionFrequency.INSTANT,
    status: str = SubscriptionStatus.ACTIVE,
    consent_source: str | None = None,
) -> tuple[Subscription, bool, bool]:
    normalized_channel = str(channel).strip().lower()
    consent = consent_source or (SubscriptionSource.USSD if normalized_channel == SubscriptionChannel.USSD else SubscriptionSource.SMS)
    subscription, created, reactivated = _upsert_subscription(
        bill,
        phone_number,
        normalized_channel,
        scope=scope,
        target_value=target_value,
        language=language,
        cadence=cadence,
        status=status,
        consent_source=consent,
    )
    effective_created = created or reactivated

    record_system_log(
        LogEventType.SUBSCRIPTION,
        f"Subscription received for {_mask_phone_number(phone_number)}.",
        {
            "billId": bill.id if bill else None,
            "phoneNumber": phone_number,
            "channel": normalized_channel,
            "scope": scope,
            "targetValue": target_value,
            "created": created,
            "reactivated": reactivated,
            "quantity": 1 if effective_created else 0,
        },
    )
    _queue_subscription_confirmation_sms(
        subscription,
        bill,
        effective_created,
        normalized_channel,
        reactivated=reactivated,
    )
    return subscription, effective_created, reactivated


def create_poll_response(bill: Bill, phone_number: str, choice: str) -> PollResponse:
    with transaction.atomic():
        response = PollResponse.objects.create(bill=bill, phone_number=phone_number, choice=choice)

        if choice == PollChoice.SUPPORT:
            petition = getattr(bill, "petition", None)
            if petition is not None:
                Petition.objects.filter(pk=petition.pk).update(signature_count=F("signature_count") + 1)

        record_system_log(
            LogEventType.VOTE,
            f"Poll response recorded for {bill.id}.",
            {
                "billId": bill.id,
                "phoneNumber": phone_number,
                "choice": choice,
                "quantity": 1,
            },
        )
        return response
