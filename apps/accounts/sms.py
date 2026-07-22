import logging

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class SMSConfigurationError(RuntimeError):
    pass


class SMSDeliveryError(RuntimeError):
    pass


def _messaging_url():
    if settings.AFRICAS_TALKING_SANDBOX:
        return "https://api.sandbox.africastalking.com/version1/messaging"

    return "https://api.africastalking.com/version1/messaging"


def send_sms(recipient, message):
    username = str(settings.AFRICAS_TALKING_USERNAME or "").strip()
    api_key = str(settings.AFRICAS_TALKING_API_KEY or "").strip()
    sender_id = str(settings.AFRICAS_TALKING_SENDER_ID or "").strip()

    if not username or not api_key:
        raise SMSConfigurationError(
            "Phone verification is not configured. Please contact QOT support."
        )

    payload = {
        "username": username,
        "to": recipient,
        "message": message,
    }

    if sender_id:
        payload["from"] = sender_id

    try:
        response = requests.post(
            _messaging_url(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "apiKey": api_key,
            },
            data=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("Africa's Talking SMS request failed: %s", type(error).__name__)
        raise SMSDeliveryError(
            "We could not send the verification code. Please try again shortly."
        ) from error

    recipients = data.get("SMSMessageData", {}).get("Recipients", [])

    if not recipients:
        logger.warning("Africa's Talking returned no SMS recipient result.")
        raise SMSDeliveryError(
            "We could not send the verification code. Please try again shortly."
        )

    result = recipients[0]
    status_name = str(result.get("status") or "").strip().lower()
    status_code = result.get("statusCode")

    if status_name not in {"success", "sent"} and status_code not in {101, 102}:
        logger.warning(
            "Africa's Talking rejected an SMS with status %s.",
            status_code or status_name or "unknown",
        )
        raise SMSDeliveryError(
            "We could not send the verification code. Please check the phone number and try again."
        )

    return {
        "message_id": result.get("messageId") or "",
        "status": result.get("status") or "",
        "cost": result.get("cost") or "",
    }
