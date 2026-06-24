import uuid

from rest_framework import serializers

from apps.listings.models import Listing

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "listing",
            "listing_title",
            "purpose",
            "amount",
            "currency",
            "payment_method",
            "status",
            "reference",
            "provider_reference",
            "notes",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "reference",
            "provider_reference",
            "notes",
            "paid_at",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Payment
        fields = [
            "listing",
            "purpose",
            "amount",
            "currency",
            "payment_method",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        listing = attrs.get("listing")
        purpose = attrs.get("purpose")

        if attrs["amount"] <= 0:
            raise serializers.ValidationError(
                {"amount": "Amount must be greater than zero."}
            )

        if purpose in [
            Payment.PURPOSE_FEATURED_LISTING,
            Payment.PURPOSE_BOOST_LISTING,
        ]:
            if not listing:
                raise serializers.ValidationError(
                    {"listing": "A listing is required for this payment purpose."}
                )

            if listing.seller != request.user:
                raise serializers.ValidationError(
                    {"listing": "You can only pay for your own listing."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        reference = f"QOT-{uuid.uuid4().hex[:12].upper()}"

        return Payment.objects.create(
            user=request.user,
            reference=reference,
            status=Payment.STATUS_PENDING,
            **validated_data,
        )


class MarkPaymentPaidSerializer(serializers.Serializer):
    provider_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class MarkPaymentFailedSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )