from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone


class BillStatus(models.TextChoices):
    FIRST_READING = "First Reading", "First Reading"
    COMMITTEE = "Committee", "Committee"
    SECOND_READING = "Second Reading", "Second Reading"
    THIRD_READING = "Third Reading", "Third Reading"
    PRESIDENTIAL_ASSENT = "Presidential Assent", "Presidential Assent"


class BillCategory(models.TextChoices):
    FINANCE = "Finance", "Finance"
    HEALTH = "Health", "Health"
    EDUCATION = "Education", "Education"
    JUSTICE = "Justice", "Justice"
    ENVIRONMENT = "Environment", "Environment"


class RepresentativeRole(models.TextChoices):
    MP = "MP", "MP"
    MCA = "MCA", "MCA"
    SENATOR = "Senator", "Senator"


class VoteChoice(models.TextChoices):
    YES = "Yes", "Yes"
    NO = "No", "No"
    ABSTAIN = "Abstain", "Abstain"


class PollChoice(models.TextChoices):
    SUPPORT = "support", "Support"
    OPPOSE = "oppose", "Oppose"
    MORE_INFO = "need_more_info", "Need more info"


class CountySentiment(models.TextChoices):
    SUPPORT = "Support", "Support"
    OPPOSE = "Oppose", "Oppose"
    MIXED = "Mixed", "Mixed"


class SubscriptionChannel(models.TextChoices):
    SMS = "sms", "SMS"
    USSD = "ussd", "USSD"


class DocumentProcessingStatus(models.TextChoices):
    UNAVAILABLE = "unavailable", "Unavailable"
    NEEDS_OCR = "needs_ocr", "Needs OCR"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class DocumentExtractionMethod(models.TextChoices):
    TEXT = "text", "Text extraction"
    OCR = "ocr", "OCR"


class LogEventType(models.TextChoices):
    STATUS_CHANGE = "status_change", "Status change"
    SMS_BROADCAST = "sms_broadcast", "SMS broadcast"
    SMS_INBOUND = "sms_inbound", "SMS inbound"
    SMS_DELIVERY_REPORT = "sms_delivery_report", "SMS delivery report"
    USSD_HIT = "ussd_hit", "USSD hit"
    SUBSCRIPTION = "subscription", "Subscription"
    VOTE = "vote", "Vote"
    SYSTEM = "system", "System"
    SCRAPE = "scrape", "Scrape"
    MESSAGE_OUTBOUND = "message_outbound", "Message outbound"
    CONSENT = "consent", "Consent"
    DIGEST = "digest", "Digest"
    WEBHOOK = "webhook", "Webhook"


class SubscriptionScope(models.TextChoices):
    BILL = "bill", "Bill"
    CATEGORY = "category", "Category"
    COUNTY = "county", "County"
    SPONSOR = "sponsor", "Sponsor"
    ALL = "all", "All bills"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    UNSUBSCRIBED = "unsubscribed", "Unsubscribed"


class SubscriptionFrequency(models.TextChoices):
    INSTANT = "instant", "Instant"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MILESTONE = "milestone", "Milestone"


class MessageLanguage(models.TextChoices):
    EN = "en", "English"
    SW = "sw", "Swahili"


class SubscriptionSource(models.TextChoices):
    SMS = "sms", "SMS"
    USSD = "ussd", "USSD"
    ADMIN = "admin", "Admin"
    API = "api", "API"


class OutboundMessageStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENDING = "sending", "Sending"
    ACCEPTED = "accepted", "Accepted"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    UNDELIVERED = "undelivered", "Undelivered"
    SKIPPED = "skipped", "Skipped"


class OutboundMessageType(models.TextChoices):
    CONFIRMATION = "confirmation", "Confirmation"
    BROADCAST = "broadcast", "Broadcast"
    DIGEST = "digest", "Digest"
    MILESTONE = "milestone", "Milestone"
    REPLY = "reply", "Reply"
    REMINDER = "reminder", "Reminder"


class WebhookEventType(models.TextChoices):
    SMS_INBOUND = "sms_inbound", "SMS inbound"
    SMS_DELIVERY_REPORT = "sms_delivery_report", "SMS delivery report"
    USSD = "ussd", "USSD"


class WebhookEventStatus(models.TextChoices):
    PROCESSED = "processed", "Processed"
    DUPLICATE = "duplicate", "Duplicate"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"


class Bill(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    status = models.CharField(max_length=32, choices=BillStatus.choices, default=BillStatus.FIRST_READING)
    category = models.CharField(max_length=32, choices=BillCategory.choices)
    date_introduced = models.DateField()
    is_hot = models.BooleanField(default=False)
    full_text_url = models.URLField(blank=True, max_length=2048)
    key_points = models.JSONField(default=list, blank=True)
    timeline = models.JSONField(default=list, blank=True)
    subscriber_count = models.PositiveIntegerField(default=0)
    document_status = models.CharField(
        max_length=16,
        choices=DocumentProcessingStatus.choices,
        default=DocumentProcessingStatus.UNAVAILABLE,
    )
    document_method = models.CharField(
        max_length=16,
        choices=DocumentExtractionMethod.choices,
        blank=True,
        default="",
    )
    document_source_url = models.URLField(blank=True, default="", max_length=2048)
    document_text = models.TextField(blank=True, default="")
    document_pages = models.JSONField(default=list, blank=True)
    document_error = models.TextField(blank=True, default="")
    document_page_count = models.PositiveIntegerField(default=0)
    document_word_count = models.PositiveIntegerField(default=0)
    document_processed_at = models.DateTimeField(null=True, blank=True)
    sponsor = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="MP, Senator, or Government who introduced the bill.",
    )
    parliament_url = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        help_text="Direct link to the bill on parliament.go.ke.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_hot", "-date_introduced", "title"]

    if TYPE_CHECKING:
        petition: Petition
        county_stats: models.Manager["CountyStat"]
        representative_votes: models.Manager["RepresentativeVote"]
        poll_responses: models.Manager["PollResponse"]
        subscriptions: models.Manager["Subscription"]
        outbound_messages: models.Manager["OutboundMessage"]

    def __str__(self) -> str:
        return self.title


class Petition(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="petition")
    title = models.CharField(max_length=255)
    description = models.TextField()
    signature_count = models.PositiveIntegerField(default=0)
    goal = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signature_count", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.bill.pk})"


class Representative(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=16, choices=RepresentativeRole.choices)
    constituency = models.CharField(max_length=255)
    county = models.CharField(max_length=255)
    party = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    if TYPE_CHECKING:
        votes: models.Manager["RepresentativeVote"]

    def __str__(self) -> str:
        return self.name


class RepresentativeVote(models.Model):
    representative = models.ForeignKey(Representative, on_delete=models.CASCADE, related_name="votes")
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="representative_votes")
    vote = models.CharField(max_length=16, choices=VoteChoice.choices)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-voted_at"]
        constraints = [
            models.UniqueConstraint(fields=["representative", "bill"], name="unique_vote_per_representative_bill"),
        ]

    if TYPE_CHECKING:
        bill_id: str

    def __str__(self) -> str:
        return f"{self.representative.pk} -> {self.bill.pk}: {self.vote}"


class CountyStat(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="county_stats", null=True, blank=True)
    county = models.CharField(max_length=255)
    engagement_count = models.PositiveIntegerField(default=0)
    sentiment = models.CharField(max_length=16, choices=CountySentiment.choices)

    class Meta:
        ordering = ["-engagement_count", "county"]
        constraints = [
            models.UniqueConstraint(fields=["bill", "county"], name="unique_county_stat_per_bill"),
        ]

    def __str__(self) -> str:
        return f"{self.county} ({self.engagement_count})"


class PollResponse(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="poll_responses")
    phone_number = models.CharField(max_length=32, blank=True)
    choice = models.CharField(max_length=24, choices=PollChoice.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.bill.pk}: {self.choice}"


class Subscription(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="subscriptions", null=True, blank=True)
    phone_number = models.CharField(max_length=32)
    channel = models.CharField(max_length=16, choices=SubscriptionChannel.choices, default=SubscriptionChannel.SMS)
    scope = models.CharField(max_length=16, choices=SubscriptionScope.choices, default=SubscriptionScope.BILL)
    target_value = models.CharField(max_length=255, blank=True, default="")
    language = models.CharField(max_length=8, choices=MessageLanguage.choices, default=MessageLanguage.EN)
    cadence = models.CharField(max_length=16, choices=SubscriptionFrequency.choices, default=SubscriptionFrequency.INSTANT)
    status = models.CharField(max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    pause_until = models.DateTimeField(null=True, blank=True)
    consent_source = models.CharField(max_length=16, choices=SubscriptionSource.choices, default=SubscriptionSource.API)
    consented_at = models.DateTimeField(default=timezone.now)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    last_digest_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number", "channel", "scope", "bill", "target_value"],
                name="unique_subscription_target_per_phone_channel",
            ),
        ]

    if TYPE_CHECKING:
        bill_id: str | None
        outbound_messages: models.Manager["OutboundMessage"]

    def __str__(self) -> str:
        bill = self.bill
        if self.scope == SubscriptionScope.BILL and bill is not None:
            target = bill.pk
        elif self.scope == SubscriptionScope.ALL:
            target = "all-bills"
        else:
            target = self.target_value or self.scope
        return f"{self.phone_number} -> {target}"


class OutboundMessage(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name="outbound_messages")
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_messages",
    )
    recipient_phone_number = models.CharField(max_length=32)
    message = models.TextField()
    message_type = models.CharField(max_length=16, choices=OutboundMessageType.choices)
    language = models.CharField(max_length=8, choices=MessageLanguage.choices, default=MessageLanguage.EN)
    status = models.CharField(max_length=16, choices=OutboundMessageStatus.choices, default=OutboundMessageStatus.QUEUED)
    provider = models.CharField(max_length=32, default="africastalking")
    provider_message_id = models.CharField(max_length=128, blank=True, default="")
    dedupe_key = models.CharField(max_length=255, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["recipient_phone_number"]),
            models.Index(fields=["message_type"]),
        ]

    if TYPE_CHECKING:
        bill_id: str | None
        subscription_id: int | None

    def __str__(self) -> str:
        return f"{self.message_type}: {self.recipient_phone_number}"

    @property
    def initial_provider_status(self) -> str:
        if isinstance(self.metadata, dict):
            return str(self.metadata.get("providerStatus") or "")
        return ""

    @property
    def initial_provider_status_code(self) -> str:
        if isinstance(self.metadata, dict):
            return str(self.metadata.get("providerStatusCode") or "")
        return ""

    @property
    def initial_provider_message(self) -> str:
        if isinstance(self.metadata, dict):
            return str(self.metadata.get("providerMessage") or "")
        return ""

    @property
    def delivery_status(self) -> str:
        if isinstance(self.metadata, dict):
            return str(self.metadata.get("deliveryStatus") or "")
        return ""

    @property
    def delivery_status_code(self) -> str:
        if isinstance(self.metadata, dict):
            return str(self.metadata.get("deliveryStatusCode") or "")
        return ""


class WebhookReceipt(models.Model):
    provider = models.CharField(max_length=32, default="africastalking")
    event_type = models.CharField(max_length=32, choices=WebhookEventType.choices)
    external_id = models.CharField(max_length=255)
    dedupe_key = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=32, blank=True, default="")
    raw_phone_number = models.CharField(max_length=32, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    response_text = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=WebhookEventStatus.choices, default=WebhookEventStatus.PROCESSED)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "event_type"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.external_id}"


class SystemLog(models.Model):
    event_type = models.CharField(max_length=32, choices=LogEventType.choices, default=LogEventType.SYSTEM)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.message[:40]}"
