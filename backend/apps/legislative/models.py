from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        bill_identifier = self.bill.pk if self.bill else "all-bills"
        return f"{self.phone_number} -> {bill_identifier}"


class SystemLog(models.Model):
    event_type = models.CharField(max_length=32, choices=LogEventType.choices, default=LogEventType.SYSTEM)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.message[:40]}"
