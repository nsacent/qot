import secrets

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SMSDeliveryReport


def _clean_value(value, max_length):
    return " ".join(str(value or "").split())[:max_length]


class AfricasTalkingSMSDeliveryWebhook(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected_token = str(
            getattr(settings, "AFRICAS_TALKING_CALLBACK_TOKEN", "") or ""
        ).strip()
        supplied_token = str(
            request.query_params.get("token")
            or request.headers.get("X-QOT-Webhook-Token")
            or ""
        ).strip()

        if not expected_token:
            return Response(
                {"detail": "SMS delivery callbacks are not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not supplied_token or not secrets.compare_digest(
            supplied_token,
            expected_token,
        ):
            return Response(
                {"detail": "Invalid callback token."},
                status=status.HTTP_403_FORBIDDEN,
            )

        provider_message_id = _clean_value(
            request.data.get("id") or request.data.get("messageId"),
            150,
        )
        if not provider_message_id:
            return Response(
                {"detail": "A provider message ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        retry_count = request.data.get("retryCount")
        try:
            retry_count = int(retry_count) if retry_count not in (None, "") else None
        except (TypeError, ValueError):
            retry_count = None

        report, _ = SMSDeliveryReport.objects.update_or_create(
            provider_message_id=provider_message_id,
            defaults={
                "phone": _clean_value(request.data.get("phoneNumber"), 20),
                "status": _clean_value(request.data.get("status"), 50),
                "status_code": _clean_value(request.data.get("statusCode"), 20),
                "network_code": _clean_value(request.data.get("networkCode"), 30),
                "failure_reason": _clean_value(request.data.get("failureReason"), 150),
                "retry_count": retry_count,
            },
        )

        return Response(
            {
                "message": "Delivery report received.",
                "id": report.provider_message_id,
            },
            status=status.HTTP_200_OK,
        )
