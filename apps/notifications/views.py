from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushDevice
from .serializers import NotificationSerializer, PushDeviceSerializer


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Notification.objects
            .filter(user=self.request.user)
            .select_related("listing", "chat_thread")
            .order_by("-created_at")
        )

        is_read = self.request.query_params.get("is_read")

        if is_read == "true":
            queryset = queryset.filter(is_read=True)

        if is_read == "false":
            queryset = queryset.filter(is_read=False)

        return queryset


class NotificationMarkReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk,
                user=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(
            {"message": "Notification marked as read."},
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response(
            {"message": "All notifications marked as read."},
            status=status.HTTP_200_OK,
        )


class PushDeviceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["expo_push_token"]
        device, created = PushDevice.objects.update_or_create(
            expo_push_token=token,
            defaults={
                "user": request.user,
                "platform": serializer.validated_data["platform"],
                "device_id": serializer.validated_data.get("device_id", ""),
                "is_active": True,
            },
        )
        return Response(
            PushDeviceSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        token = str(request.data.get("expo_push_token", "")).strip()
        if not token:
            return Response(
                {"expo_push_token": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PushDevice.objects.filter(
            user=request.user,
            expo_push_token=token,
        ).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
