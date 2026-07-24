from django.core.cache import cache


PRESENCE_TIMEOUT_SECONDS = 90


def _presence_key(user_id):
    return f"chat:presence:user:{user_id}"


def connect_user(user_id):
    key = _presence_key(user_id)

    if cache.add(key, 1, timeout=PRESENCE_TIMEOUT_SECONDS):
        return 1

    try:
        connections = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=PRESENCE_TIMEOUT_SECONDS)
        return 1

    cache.touch(key, PRESENCE_TIMEOUT_SECONDS)
    return connections


def refresh_user(user_id):
    key = _presence_key(user_id)

    if cache.get(key) is None:
        cache.set(key, 1, timeout=PRESENCE_TIMEOUT_SECONDS)
        return 1

    cache.touch(key, PRESENCE_TIMEOUT_SECONDS)
    return int(cache.get(key) or 1)


def disconnect_user(user_id):
    key = _presence_key(user_id)

    try:
        connections = cache.decr(key)
    except ValueError:
        cache.delete(key)
        return 0

    if connections <= 0:
        cache.delete(key)
        return 0

    cache.touch(key, PRESENCE_TIMEOUT_SECONDS)
    return connections


def is_user_online(user_id):
    if not user_id:
        return False

    try:
        return int(cache.get(_presence_key(user_id)) or 0) > 0
    except Exception:
        # Presence is optional; an unavailable cache must not break the inbox.
        return False
