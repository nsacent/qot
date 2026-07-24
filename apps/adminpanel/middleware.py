import json
import ipaddress
import logging

from .models import AdminActivityLog


logger = logging.getLogger(__name__)

ADMIN_PATH_PREFIX = "/api/v1/admin-panel/"
MODERATION_PATH_PREFIX = "/api/v1/moderation/"
TRACE_PATH_PREFIXES = (ADMIN_PATH_PREFIX, MODERATION_PATH_PREFIX)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_JSON_BODY_BYTES = 64 * 1024
SENSITIVE_KEY_PARTS = {
    "authorization",
    "cookie",
    "key",
    "otp",
    "password",
    "secret",
    "token",
}


ACTION_NAMES = {
    "approve": ("listing.approve", "Approved ad"),
    "reject": ("listing.reject", "Rejected ad"),
    "feature": ("listing.feature", "Featured ad"),
    "unfeature": ("listing.unfeature", "Removed ad feature"),
    "delete": ("listing.delete", "Removed ad"),
    "ban": ("user.ban", "Restricted user"),
    "unban": ("user.unban", "Restored user access"),
    "mark-paid": ("payment.mark_paid", "Marked payment as paid"),
    "mark-failed": ("payment.mark_failed", "Marked payment as failed"),
    "cancel": ("payment.cancel", "Cancelled payment"),
    "hide": ("review.hide", "Hid seller review"),
    "show": ("review.show", "Restored seller review"),
    "resolve": ("chat_report.resolve", "Resolved chat report"),
    "restore": ("backup.restore", "Restored database backup"),
}

RESOURCE_NAMES = {
    "backups": "database backup",
    "chat-reports": "chat report",
    "listings": "ad",
    "packages": "promotion package",
    "payments": "payment",
    "reviews": "seller review",
    "users": "user",
}


def _sanitise_payload(value, depth=0):
    if depth > 4:
        return "[truncated]"

    if isinstance(value, dict):
        clean = {}
        for key, item in list(value.items())[:30]:
            key_text = str(key)
            normalised_key = key_text.lower().replace("-", "_")
            if any(part in normalised_key for part in SENSITIVE_KEY_PARTS):
                clean[key_text] = "[redacted]"
            else:
                clean[key_text] = _sanitise_payload(item, depth + 1)
        return clean

    if isinstance(value, (list, tuple)):
        return [_sanitise_payload(item, depth + 1) for item in list(value)[:20]]

    if isinstance(value, str):
        return value[:500]

    if value is None or isinstance(value, (bool, int, float)):
        return value

    return str(value)[:500]


def _read_json_payload(request):
    content_type = request.META.get("CONTENT_TYPE", "").lower()
    try:
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        content_length = 0

    if not content_type.startswith("application/json"):
        return {}

    if content_length > MAX_JSON_BODY_BYTES:
        return {"_note": "Request body omitted because it was too large."}

    try:
        raw_body = request.body.decode("utf-8")
        if not raw_body:
            return {}
        return _sanitise_payload(json.loads(raw_body))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return {"_note": "Request body could not be decoded."}


def _request_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = (
        forwarded_for.split(",", 1)[0].strip()
        if forwarded_for
        else request.META.get("REMOTE_ADDR", "").strip()
    )

    try:
        return str(ipaddress.ip_address(candidate)) if candidate else None
    except ValueError:
        return None


def _describe_action(method, path):
    if path.startswith(MODERATION_PATH_PREFIX):
        relative_path = path.removeprefix(MODERATION_PATH_PREFIX)
        parts = [part for part in relative_path.split("/") if part]
        target_id = parts[1] if len(parts) > 1 else ""
        operation = parts[2] if len(parts) > 2 else ""
        suffix = f" #{target_id}" if target_id else ""

        moderation_actions = {
            "resolve": ("report.resolve", f"Resolved listing report{suffix}"),
            "reject-listing": ("listing.reject", f"Rejected reported ad{suffix}"),
            "delete-listing": ("listing.delete", f"Removed reported ad{suffix}"),
        }
        action, description = moderation_actions.get(
            operation,
            ("report.update", f"Updated listing report{suffix}"),
        )
        return action, description, "listing report", target_id

    relative_path = path.removeprefix(ADMIN_PATH_PREFIX)
    parts = [part for part in relative_path.split("/") if part]
    resource = parts[0] if parts else "admin"
    target_id = parts[1] if len(parts) > 1 else ""
    operation = parts[2] if len(parts) > 2 else ""
    target_type = RESOURCE_NAMES.get(resource, resource.replace("-", " "))

    if operation in ACTION_NAMES:
        action, label = ACTION_NAMES[operation]
        suffix = f" #{target_id}" if target_id else ""
        return action, f"{label}{suffix}", target_type, target_id

    if resource == "backups" and method == "POST":
        return "backup.create", "Created database backup", target_type, target_id

    if method == "POST" and not target_id:
        return f"{resource}.create", f"Created {target_type}", target_type, ""

    verb = {
        "DELETE": "Deleted",
        "PATCH": "Updated",
        "POST": "Updated",
        "PUT": "Updated",
    }.get(method, "Changed")
    suffix = f" #{target_id}" if target_id else ""
    return f"{resource}.{method.lower()}", f"{verb} {target_type}{suffix}", target_type, target_id


class AdminActivityAuditMiddleware:
    """Persist every state-changing staff moderation request after it completes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        should_trace = (
            request.method in MUTATING_METHODS
            and request.path.startswith(TRACE_PATH_PREFIXES)
            and not request.path.startswith(f"{ADMIN_PATH_PREFIX}activity/")
        )
        payload = _read_json_payload(request) if should_trace else {}
        response = self.get_response(request)

        if should_trace:
            self._record(request, response, payload)

        return response

    def _record(self, request, response, payload):
        user = getattr(request, "user", None)
        role = str(getattr(user, "role", "") or "").lower()
        is_staff_actor = bool(
            user
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_staff", False) or role in {"admin", "moderator"})
        )

        if not is_staff_actor:
            return

        action, description, target_type, target_id = _describe_action(
            request.method,
            request.path,
        )

        try:
            AdminActivityLog.objects.create(
                actor=user,
                actor_name=getattr(user, "full_name", "") or "",
                actor_email=getattr(user, "email", "") or "",
                actor_role=role or ("admin" if getattr(user, "is_superuser", False) else "staff"),
                action=action,
                description=description,
                method=request.method,
                path=request.get_full_path()[:500],
                target_type=target_type[:80],
                target_id=target_id[:180],
                status_code=response.status_code,
                ip_address=_request_ip(request),
                payload=payload,
            )
        except Exception:
            logger.exception("Unable to record admin activity for %s", request.path)
