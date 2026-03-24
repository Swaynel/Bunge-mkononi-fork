from rest_framework import serializers

from .models import (
    Bill,
    CountyStat,
    Petition,
    PollChoice,
    PollResponse,
    Representative,
    RepresentativeVote,
    Subscription,
    SubscriptionChannel,
    SystemLog,
)


class PetitionSummarySerializer(serializers.ModelSerializer):
    signatureCount = serializers.IntegerField(source="signature_count", read_only=True)
    progressPercent = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ["id", "title", "description", "signatureCount", "goal", "progressPercent"]
        read_only_fields = fields

    def get_progressPercent(self, obj: Petition) -> float:
        if not obj.goal:
            return 0
        return round((obj.signature_count / obj.goal) * 100, 1)


class PetitionSerializer(serializers.ModelSerializer):
    billId = serializers.PrimaryKeyRelatedField(source="bill", queryset=Bill.objects.all())
    signatureCount = serializers.IntegerField(source="signature_count")
    progressPercent = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Petition
        fields = ["id", "billId", "title", "description", "signatureCount", "goal", "progressPercent", "createdAt"]

    def get_progressPercent(self, obj: Petition) -> float:
        if not obj.goal:
            return 0
        return round((obj.signature_count / obj.goal) * 100, 1)


class RepresentativeSummarySerializer(serializers.ModelSerializer):
    imageUrl = serializers.URLField(source="image_url", allow_blank=True, required=False)

    class Meta:
        model = Representative
        fields = ["id", "name", "role", "constituency", "county", "party", "imageUrl"]


class RepresentativeVoteNestedSerializer(serializers.ModelSerializer):
    billId = serializers.CharField(source="bill_id", read_only=True)
    billTitle = serializers.CharField(source="bill.title", read_only=True)
    representative = RepresentativeSummarySerializer(read_only=True)
    votedAt = serializers.DateTimeField(source="voted_at", read_only=True)

    class Meta:
        model = RepresentativeVote
        fields = ["id", "billId", "billTitle", "representative", "vote", "votedAt"]


class RepresentativeSerializer(serializers.ModelSerializer):
    imageUrl = serializers.URLField(source="image_url", allow_blank=True, required=False)
    recentVotes = serializers.SerializerMethodField()

    class Meta:
        model = Representative
        fields = ["id", "name", "role", "constituency", "county", "party", "imageUrl", "recentVotes"]

    def get_recentVotes(self, obj: Representative):
        bill_id = self.context.get("bill_id")
        votes = obj.votes.select_related("bill").order_by("-voted_at")
        if bill_id:
            votes = votes.filter(bill_id=bill_id)
        else:
            votes = votes[:5]

        return [
            {
                "billId": vote.bill_id,
                "billTitle": vote.bill.title,
                "vote": vote.vote,
            }
            for vote in votes
        ]


class CountyStatSerializer(serializers.ModelSerializer):
    billId = serializers.CharField(source="bill_id", read_only=True)
    engagementCount = serializers.IntegerField(source="engagement_count")

    class Meta:
        model = CountyStat
        fields = ["billId", "county", "engagementCount", "sentiment"]


class SubscriptionSerializer(serializers.ModelSerializer):
    billId = serializers.PrimaryKeyRelatedField(source="bill", queryset=Bill.objects.all(), required=False, allow_null=True)
    phoneNumber = serializers.CharField(source="phone_number")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    channel = serializers.ChoiceField(choices=SubscriptionChannel.choices, required=False)

    class Meta:
        model = Subscription
        fields = ["id", "billId", "phoneNumber", "channel", "createdAt"]


class PollResponseSerializer(serializers.ModelSerializer):
    billId = serializers.PrimaryKeyRelatedField(source="bill", queryset=Bill.objects.all())
    phoneNumber = serializers.CharField(source="phone_number", required=False, allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = PollResponse
        fields = ["id", "billId", "phoneNumber", "choice", "createdAt"]


class SystemLogSerializer(serializers.ModelSerializer):
    eventType = serializers.CharField(source="event_type")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = SystemLog
        fields = ["id", "eventType", "message", "metadata", "createdAt"]


class BillSerializer(serializers.ModelSerializer):
    dateIntroduced = serializers.DateField(source="date_introduced")
    isHot = serializers.BooleanField(source="is_hot", required=False)
    fullTextUrl = serializers.URLField(source="full_text_url", allow_blank=True, required=False)
    keyPoints = serializers.JSONField(source="key_points", required=False)
    subscriberCount = serializers.IntegerField(source="subscriber_count", required=False)
    currentStage = serializers.CharField(source="status", read_only=True)
    parliamentUrl = serializers.URLField(
        source="parliament_url",
        allow_blank=True,
        required=False,
        help_text="Direct link to the bill on parliament.go.ke.",
    )
    petition = serializers.SerializerMethodField()
    petitionSignatureCount = serializers.SerializerMethodField()
    petitionGoal = serializers.SerializerMethodField()
    petitionProgressPercent = serializers.SerializerMethodField()
    polling = serializers.SerializerMethodField()
    representativeVotes = serializers.SerializerMethodField()
    countyStats = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id",
            "title",
            "summary",
            "status",
            "category",
            "sponsor",
            "parliamentUrl",
            "dateIntroduced",
            "isHot",
            "fullTextUrl",
            "keyPoints",
            "timeline",
            "subscriberCount",
            "currentStage",
            "petition",
            "petitionSignatureCount",
            "petitionGoal",
            "petitionProgressPercent",
            "polling",
            "representativeVotes",
            "countyStats",
            "createdAt",
            "updatedAt",
        ]

    def get_petition(self, obj: Bill):
        petition = getattr(obj, "petition", None)
        if not petition:
            return None
        return PetitionSummarySerializer(petition).data

    def get_petitionSignatureCount(self, obj: Bill) -> int:
        petition = getattr(obj, "petition", None)
        return petition.signature_count if petition else 0

    def get_petitionGoal(self, obj: Bill) -> int:
        petition = getattr(obj, "petition", None)
        return petition.goal if petition else 0

    def get_petitionProgressPercent(self, obj: Bill) -> float:
        petition = getattr(obj, "petition", None)
        if not petition or not petition.goal:
            return 0
        return round((petition.signature_count / petition.goal) * 100, 1)

    def get_polling(self, obj: Bill):
        responses = obj.poll_responses.all()
        return {
            "yes": responses.filter(choice=PollChoice.SUPPORT).count(),
            "no": responses.filter(choice=PollChoice.OPPOSE).count(),
            "undecided": responses.filter(choice=PollChoice.MORE_INFO).count(),
        }

    def get_representativeVotes(self, obj: Bill):
        votes = obj.representative_votes.select_related("representative").order_by("-voted_at")
        return RepresentativeVoteNestedSerializer(votes, many=True).data

    def get_countyStats(self, obj: Bill):
        counties = obj.county_stats.all().order_by("-engagement_count", "county")
        return CountyStatSerializer(counties, many=True).data


class BillDetailSerializer(BillSerializer):
    documentStatus = serializers.CharField(source="document_status", read_only=True)
    documentMethod = serializers.CharField(source="document_method", read_only=True)
    documentSourceUrl = serializers.CharField(source="document_source_url", read_only=True)
    documentText = serializers.CharField(source="document_text", read_only=True)
    documentPages = serializers.JSONField(source="document_pages", read_only=True)
    documentError = serializers.CharField(source="document_error", read_only=True)
    documentPageCount = serializers.IntegerField(source="document_page_count", read_only=True)
    documentWordCount = serializers.IntegerField(source="document_word_count", read_only=True)
    documentProcessedAt = serializers.DateTimeField(source="document_processed_at", read_only=True, allow_null=True)

    class Meta(BillSerializer.Meta):
        fields = BillSerializer.Meta.fields + [
            "documentStatus",
            "documentMethod",
            "documentSourceUrl",
            "documentText",
            "documentPages",
            "documentError",
            "documentPageCount",
            "documentWordCount",
            "documentProcessedAt",
        ]


class ScrapeTriggerSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False,
        default="https://www.parliament.go.ke/the-national-assembly/house-business/bills",
        help_text="Override the default parliament bills page URL.",
    )
    timeout = serializers.IntegerField(
        required=False,
        default=30,
        min_value=5,
        max_value=120,
        help_text="HTTP request timeout in seconds.",
    )


class BillVoteCountyBreakdownSerializer(serializers.Serializer):
    county = serializers.CharField()
    yes = serializers.IntegerField()
    no = serializers.IntegerField()
    abstain = serializers.IntegerField()
    total = serializers.IntegerField()


class BillVoteSummarySerializer(serializers.Serializer):
    billId = serializers.CharField()
    billTitle = serializers.CharField()
    billStatus = serializers.CharField(required=False, allow_blank=True)
    totalVotes = serializers.IntegerField()
    yes = serializers.IntegerField()
    no = serializers.IntegerField()
    abstain = serializers.IntegerField()
    yesPercent = serializers.FloatField()
    noPercent = serializers.FloatField()
    abstainPercent = serializers.FloatField()
    byCounty = BillVoteCountyBreakdownSerializer(many=True)
    byParty = serializers.DictField(child=serializers.DictField(child=serializers.IntegerField()))


class ScrapeRepresentativesTriggerSerializer(serializers.Serializer):
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
        required=False,
        default=30,
        min_value=5,
        max_value=120,
    )


class ScrapeVotesTriggerSerializer(serializers.Serializer):
    bill_id = serializers.CharField(
        help_text="Bill.id to associate vote records with.",
    )
    url = serializers.URLField(
        help_text="URL of the Hansard division page.",
    )
    timeout = serializers.IntegerField(
        required=False,
        default=30,
        min_value=5,
        max_value=120,
    )
