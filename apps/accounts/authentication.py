from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import UserSession


class SessionAwareJWTAuthentication(JWTAuthentication):
    """Reject access tokens that belong to a remotely signed-out device."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        session_id = validated_token.get("session_id")

        # Tokens created before device tracking was introduced remain valid and
        # are upgraded to a tracked session by the mobile app's settings page.
        if not session_id:
            return user

        now = timezone.now()
        session = UserSession.objects.filter(
            id=session_id,
            user=user,
            is_active=True,
            expires_at__gt=now,
        ).first()
        if session is None:
            raise AuthenticationFailed(
                "This device has been signed out. Please sign in again.",
                code="device_signed_out",
            )

        if session.last_seen_at < now - timedelta(minutes=5):
            UserSession.objects.filter(pk=session.pk).update(last_seen_at=now)

        return user
