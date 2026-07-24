from django.contrib.auth import get_user_model
from django.core import signing


CHAT_SOCKET_TICKET_SALT = "qot.chats.socket"
CHAT_SOCKET_TICKET_MAX_AGE_SECONDS = 120


def create_chat_socket_ticket(user):
    return signing.dumps(
        {"user_id": user.pk},
        salt=CHAT_SOCKET_TICKET_SALT,
        compress=True,
    )


def get_user_from_chat_socket_ticket(ticket):
    payload = signing.loads(
        ticket,
        salt=CHAT_SOCKET_TICKET_SALT,
        max_age=CHAT_SOCKET_TICKET_MAX_AGE_SECONDS,
    )
    user_id = payload.get("user_id")

    if not user_id:
        raise signing.BadSignature("Chat socket ticket has no user.")

    return get_user_model().objects.get(pk=user_id, is_active=True)
