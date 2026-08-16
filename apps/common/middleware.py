import hashlib
import threading
import time

from django.http import JsonResponse


PUSH_DEVICE_PATH = "/api/v1/notifications/devices/"


class PushDeviceRegistrationDedupeMiddleware:
    """Keep buggy/older clients from flooding push-device registration."""

    window_seconds = 10
    _recent = {}
    _lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._recent.clear()

    def __call__(self, request):
        if request.method != "POST" or request.path != PUSH_DEVICE_PATH:
            return self.get_response(request)

        device_id = str(request.headers.get("X-QOT-Device-ID", "")).strip()
        authorization = str(request.headers.get("Authorization", "")).strip()
        if not device_id or not authorization:
            return self.get_response(request)

        auth_fingerprint = hashlib.sha256(
            authorization.encode("utf-8")
        ).hexdigest()[:16]
        key = f"{device_id}:{auth_fingerprint}"
        now = time.monotonic()

        with self._lock:
            previous = self._recent.get(key)
            self._recent[key] = now
            if len(self._recent) > 2_000:
                cutoff = now - self.window_seconds
                self._recent = {
                    item_key: seen_at
                    for item_key, seen_at in self._recent.items()
                    if seen_at >= cutoff
                }

        if previous is not None and now - previous < self.window_seconds:
            return JsonResponse(
                {
                    "message": "Device alert registration is already in progress.",
                    "deduplicated": True,
                },
                status=200,
            )

        return self.get_response(request)
