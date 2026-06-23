from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import ChatThread, ChatMessage
from apps.listings.models import Listing
from apps.notifications.models import Notification


class MyCountsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()

        unread_chat_threads = ChatThread.objects.filter(
            buyer=user,
            buyer_unread_count__gt=0,
        ).count() + ChatThread.objects.filter(
            seller=user,
            seller_unread_count__gt=0,
        ).count()

        unread_messages = ChatMessage.objects.filter(
            thread__buyer=user,
            is_read=False,
        ).exclude(
            sender=user,
        ).count() + ChatMessage.objects.filter(
            thread__seller=user,
            is_read=False,
        ).exclude(
            sender=user,
        ).count()

        my_listings = Listing.objects.filter(
            seller=user,
        ).exclude(
            status=Listing.STATUS_DELETED,
        )

        data = {
            "unread_notifications": unread_notifications,
            "unread_chat_threads": unread_chat_threads,
            "unread_messages": unread_messages,
            "my_listings": {
                "total": my_listings.count(),
                "active": my_listings.filter(status=Listing.STATUS_ACTIVE).count(),
                "pending": my_listings.filter(status=Listing.STATUS_PENDING).count(),
                "rejected": my_listings.filter(status=Listing.STATUS_REJECTED).count(),
                "sold": my_listings.filter(status=Listing.STATUS_SOLD).count(),
                "expired": my_listings.filter(status=Listing.STATUS_EXPIRED).count(),
            },
        }

        return Response(data, status=status.HTTP_200_OK)