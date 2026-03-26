from django.contrib import admin

from .models import (
    Bill,
    CountyStat,
    OutboundMessage,
    Petition,
    PollResponse,
    Representative,
    RepresentativeVote,
    Subscription,
    SystemLog,
    WebhookReceipt,
)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "sponsor",
        "status",
        "category",
        "document_status",
        "document_method",
        "document_processed_at",
        "date_introduced",
        "is_hot",
        "subscriber_count",
        "created_at",
    )
    list_filter = ("status", "category", "is_hot", "document_status", "document_method")
    search_fields = ("id", "title", "summary", "sponsor")
    ordering = ("-is_hot", "-date_introduced", "title")


@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    list_display = ("id", "bill", "title", "signature_count", "goal", "created_at")
    list_filter = ("created_at",)
    search_fields = ("id", "title", "description", "bill__title")


@admin.register(Representative)
class RepresentativeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "role", "constituency", "county", "party", "created_at")
    list_filter = ("role", "county", "party")
    search_fields = ("id", "name", "constituency", "county", "party")


@admin.register(RepresentativeVote)
class RepresentativeVoteAdmin(admin.ModelAdmin):
    list_display = ("representative", "bill", "vote", "voted_at")
    list_filter = ("vote", "voted_at")
    search_fields = ("representative__name", "bill__title")


@admin.register(CountyStat)
class CountyStatAdmin(admin.ModelAdmin):
    list_display = ("county", "bill", "engagement_count", "sentiment")
    list_filter = ("sentiment",)
    search_fields = ("county", "bill__title")


@admin.register(PollResponse)
class PollResponseAdmin(admin.ModelAdmin):
    list_display = ("bill", "phone_number", "choice", "created_at")
    list_filter = ("choice", "created_at")
    search_fields = ("bill__title", "phone_number")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("bill", "phone_number", "channel", "scope", "status", "language", "created_at")
    list_filter = ("channel", "scope", "status", "language", "cadence", "created_at")
    search_fields = ("bill__title", "phone_number", "target_value")


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = (
        "recipient_phone_number",
        "message_type",
        "status",
        "provider_status",
        "provider_status_code",
        "delivery_status",
        "language",
        "provider_message_id",
        "failure_reason",
        "scheduled_for",
        "created_at",
    )
    list_filter = ("message_type", "status", "language", "provider", "created_at")
    search_fields = ("recipient_phone_number", "message", "provider_message_id", "dedupe_key", "last_error")
    ordering = ("-created_at",)

    @admin.display(description="Provider status")
    def provider_status(self, obj: OutboundMessage) -> str:
        return obj.initial_provider_status or "-"

    @admin.display(description="Provider code")
    def provider_status_code(self, obj: OutboundMessage) -> str:
        return obj.initial_provider_status_code or "-"

    @admin.display(description="Delivery status")
    def delivery_status(self, obj: OutboundMessage) -> str:
        return obj.delivery_status or "-"

    @admin.display(description="Failure reason")
    def failure_reason(self, obj: OutboundMessage) -> str:
        return obj.last_error or "-"


@admin.register(WebhookReceipt)
class WebhookReceiptAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_type", "external_id", "phone_number", "status", "processed_at", "created_at")
    list_filter = ("provider", "event_type", "status", "created_at")
    search_fields = ("external_id", "phone_number", "raw_phone_number", "dedupe_key")
    ordering = ("-created_at",)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "message", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("message", "event_type")
    ordering = ("-created_at",)
