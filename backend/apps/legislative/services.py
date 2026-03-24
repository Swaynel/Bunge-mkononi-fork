from __future__ import annotations

import re

from django.db import transaction
from django.db.models import F
from django.utils.text import slugify

from .africastalking import AfricaTalkingConfigurationError, AfricaTalkingError, send_sms, summarize_sms_response
from .models import Bill, LogEventType, Petition, PollChoice, PollResponse, Subscription, SubscriptionChannel, SystemLog


SMS_SUBSCRIPTION_KEYWORDS = {"SUBSCRIBE", "TRACK", "FOLLOW", "JOIN"}
SMS_STATUS_KEYWORDS = {"STATUS", "DETAIL", "DETAILS", "CURRENT"}
SMS_HELP_KEYWORDS = {"HELP", "INFO", "MENU", "START"}
SMS_UNSUBSCRIBE_KEYWORDS = {"STOP", "UNSUBSCRIBE", "CANCEL", "REMOVE"}
SMS_DELIVERY_SUCCESS_STATUSES = {"success", "delivered", "sent"}
SMS_DELIVERY_FAILURE_STATUSES = {"failed", "undelivered", "rejected", "expired", "expired_failed"}


def record_system_log(event_type: str, message: str, metadata: dict | None = None) -> SystemLog:
    return SystemLog.objects.create(event_type=event_type, message=message, metadata=metadata or {})


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


def _build_status_change_sms_message(bill: Bill, previous_status: str, new_status: str) -> str:
    return f"Update for {bill.title}: {previous_status} -> {new_status}. Reply STATUS {bill.id} for details."


def _build_subscription_confirmation_sms(bill: Bill, created: bool) -> str:
    summary = _format_bill_sms_summary(bill)
    lead = f"You are now subscribed to {bill.title}." if created else f"You are already subscribed to {bill.title}."
    return (
        f"{lead}\n"
        f"Bill ID: {bill.id}\n"
        f"{summary}\n"
        f"Reply STATUS {bill.id} for the latest update."
    )


def _queue_subscription_confirmation_sms(subscription: Subscription, bill: Bill | None, created: bool, channel: str) -> None:
    if bill is None:
        return

    if str(channel).strip().lower() != SubscriptionChannel.USSD:
        return

    phone_number = subscription.phone_number.strip()
    if not phone_number:
        return

    message = _build_subscription_confirmation_sms(bill, created)

    def _send_confirmation() -> None:
        try:
            send_sms(message, [phone_number], enqueue=True)
        except (AfricaTalkingConfigurationError, AfricaTalkingError) as exc:
            record_system_log(
                LogEventType.SYSTEM,
                f"Subscription confirmation SMS failed for {bill.title}: {exc}",
                {
                    "billId": bill.id,
                    "phoneNumber": phone_number,
                    "channel": channel,
                    "created": created,
                    "error": str(exc),
                    "quantity": 0,
                },
            )

    transaction.on_commit(_send_confirmation)


def parse_sms_subscription_command(message: str) -> tuple[str, str]:
    text = (message or "").strip()
    if not text:
        return ("help", "")

    parts = text.split(None, 1)
    command = parts[0].upper()
    remainder = parts[1].strip() if len(parts) > 1 else ""

    if command in SMS_HELP_KEYWORDS:
        return ("help", "")

    if command in SMS_UNSUBSCRIBE_KEYWORDS:
        return ("unsubscribe", remainder)

    if command in SMS_STATUS_KEYWORDS:
        return ("status", remainder)

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

    if command == "help":
        response_message = (
            "Send TRACK <bill id or bill title> to subscribe to a bill. "
            "Send STATUS <bill id or bill title> to check the latest bill update. "
            "Use the admin page to manage subscriptions."
        )
        metadata["action"] = "help"
        record_system_log(
            LogEventType.SMS_INBOUND,
            f"SMS inbound help request from {phone_number or 'unknown number'}.",
            metadata,
        )
        return {
            "action": "help",
            "phone_number": phone_number,
            "message": message_text,
            "response_message": response_message,
            "bill": None,
            "created": False,
        }

    if command == "unsubscribe":
        response_message = (
            "Unsubscribe is not automated yet. Use the admin page to remove a subscription."
        )
        metadata["action"] = "unsubscribe"
        record_system_log(
            LogEventType.SMS_INBOUND,
            f"SMS inbound unsubscribe request from {phone_number or 'unknown number'}.",
            metadata,
        )
        return {
            "action": "unsubscribe",
            "phone_number": phone_number,
            "message": message_text,
            "response_message": response_message,
            "bill": None,
            "created": False,
        }

    if command == "status":
        summary = _format_bill_sms_summary(bill)
        metadata.update(
            {
                "action": "status",
                "billId": bill.id,
                "billTitle": bill.title,
            }
        )
        record_system_log(
            LogEventType.SMS_INBOUND,
            f"SMS inbound bill status lookup for {bill.title} from {phone_number or 'unknown number'}.",
            metadata,
        )
        response_message = (
            f"{bill.title}\n"
            f"Bill ID: {bill.id}\n"
            f"{summary}\n"
            f"Reply TRACK {bill.id} to subscribe."
        )
        return {
            "action": "status",
            "phone_number": phone_number,
            "message": message_text,
            "response_message": response_message,
            "bill": bill,
            "created": False,
        }

    if not phone_number:
        response_message = "We could not read your phone number."
        metadata["action"] = "missing_phone"
        record_system_log(
            LogEventType.SMS_INBOUND,
            "SMS inbound subscription was missing a phone number.",
            metadata,
        )
        return {
            "action": "subscribe",
            "phone_number": "",
            "message": message_text,
            "response_message": response_message,
            "bill": None,
            "created": False,
        }

    bill = resolve_bill_reference(reference)
    if not bill:
        response_message = (
            "We could not match that bill. Send TRACK followed by the bill title or bill ID."
        )
        metadata["action"] = "unknown_bill"
        record_system_log(
            LogEventType.SMS_INBOUND,
            f"SMS inbound subscription could not resolve a bill from {phone_number or 'unknown number'}.",
            metadata,
        )
        return {
            "action": "subscribe",
            "phone_number": phone_number,
            "message": message_text,
            "response_message": response_message,
            "bill": None,
            "created": False,
        }

    summary = _format_bill_sms_summary(bill)
    subscription, created = create_subscription(bill, phone_number, "sms")
    metadata.update(
        {
            "action": "subscribe",
            "billId": bill.id,
            "billTitle": bill.title,
            "created": created,
        }
    )

    record_system_log(
        LogEventType.SMS_INBOUND,
        f"SMS inbound subscription for {bill.title} from {phone_number or 'unknown number'}.",
        metadata,
    )

    response_message = (
        f"You are subscribed to {bill.title}."
        if created
        else f"You are already subscribed to {bill.title}."
    )
    response_message = (
        f"{response_message}\n"
        f"{bill.title}\n"
        f"Bill ID: {bill.id}\n"
        f"{summary}\n"
        f"Reply STATUS {bill.id} for the latest bill update."
    )
    return {
        "action": "subscribe",
        "phone_number": phone_number,
        "message": message_text,
        "response_message": response_message,
        "bill": bill,
        "subscription": subscription,
        "created": created,
    }


def record_sms_delivery_report(payload: dict | None) -> dict:
    message_id = _metadata_value(payload, "id", "messageId", "message_id", "requestId")
    raw_phone_number = _metadata_value(payload, "phoneNumber", "to", "number", "recipient")
    phone_number = normalize_kenyan_phone_number(raw_phone_number) or raw_phone_number
    status = _metadata_value(payload, "status", "deliveryStatus", "state") or "unknown"
    bill = resolve_bill_from_message_id(message_id)

    metadata = {
        "messageId": message_id,
        "phoneNumber": phone_number,
        "rawPhoneNumber": raw_phone_number,
        "status": status,
        "normalizedStatus": status.lower(),
        "cost": _metadata_value(payload, "cost", "messageCost"),
        "network": _metadata_value(payload, "network", "networkCode"),
        "billId": bill.id if bill else None,
        "billTitle": bill.title if bill else None,
        "quantity": 1,
    }

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
            broadcast_bill_update(bill, _build_status_change_sms_message(bill, previous_status, new_status))
        except AfricaTalkingError:
            return

    transaction.on_commit(_notify_subscribers)
    return bill


def broadcast_bill_update(bill: Bill, message: str) -> SystemLog:
    recipients = list(
        dict.fromkeys(
            Subscription.objects.filter(bill=bill)
            .exclude(phone_number="")
            .values_list("phone_number", flat=True)
        )
    )

    if not recipients:
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

    try:
        response = send_sms(message, recipients, enqueue=True)
    except AfricaTalkingConfigurationError as exc:
        metadata = {
            "billId": bill.id,
            "subscriberCount": bill.subscriber_count,
            "recipientCount": len(recipients),
            "successfulCount": 0,
            "failedCount": len(recipients),
            "quantity": 0,
            "provider": "africastalking",
            "error": str(exc),
        }
        record_system_log(
            LogEventType.SMS_BROADCAST,
            f"SMS broadcast failed for {bill.title}: {exc}",
            metadata,
        )
        raise
    except AfricaTalkingError as exc:
        metadata = {
            "billId": bill.id,
            "subscriberCount": bill.subscriber_count,
            "recipientCount": len(recipients),
            "successfulCount": 0,
            "failedCount": len(recipients),
            "quantity": 0,
            "provider": "africastalking",
            "error": str(exc),
        }
        record_system_log(
            LogEventType.SMS_BROADCAST,
            f"SMS broadcast failed for {bill.title}: {exc}",
            metadata,
        )
        raise

    summary = summarize_sms_response(response)
    delivered_count = summary["successfulCount"] if summary["recipientCount"] else len(recipients)
    recipient_details = summary.get("recipients", []) if isinstance(summary.get("recipients", []), list) else []
    message_ids = [
        str(recipient.get("messageId") or "").strip()
        for recipient in recipient_details
        if isinstance(recipient, dict) and str(recipient.get("messageId") or "").strip()
    ]
    metadata = {
        "billId": bill.id,
        "subscriberCount": bill.subscriber_count,
        "recipientCount": len(recipients),
        "successfulCount": delivered_count,
        "failedCount": max(len(recipients) - delivered_count, 0),
        "quantity": delivered_count,
        "provider": summary["provider"],
        "providerMessage": summary["providerMessage"],
        "recipientDetails": recipient_details,
        "messageIds": message_ids,
    }
    return record_system_log(LogEventType.SMS_BROADCAST, message, metadata)


def create_subscription(bill: Bill | None, phone_number: str, channel: str) -> tuple[Subscription, bool]:
    phone_number = normalize_kenyan_phone_number(phone_number) or phone_number.strip()

    with transaction.atomic():
        subscription, created = Subscription.objects.get_or_create(
            bill=bill,
            phone_number=phone_number,
            defaults={"channel": channel},
        )

        if created and bill is not None:
            Bill.objects.filter(pk=bill.pk).update(subscriber_count=F("subscriber_count") + 1)
            bill.refresh_from_db(fields=["subscriber_count"])

        record_system_log(
            LogEventType.SUBSCRIPTION,
            f"Subscription received for {phone_number}.",
            {
                "billId": bill.id if bill else None,
                "phoneNumber": phone_number,
                "channel": channel,
                "created": created,
                "quantity": 1 if created else 0,
            },
        )
        _queue_subscription_confirmation_sms(subscription, bill, created, channel)
        return subscription, created


def create_poll_response(bill: Bill, phone_number: str, choice: str) -> PollResponse:
    with transaction.atomic():
        response = PollResponse.objects.create(bill=bill, phone_number=phone_number, choice=choice)

        if choice == PollChoice.SUPPORT:
            petition = getattr(bill, "petition", None)
            if petition is not None:
                Petition.objects.filter(pk=petition.pk).update(signature_count=F("signature_count") + 1)
                petition.refresh_from_db(fields=["signature_count"])

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
