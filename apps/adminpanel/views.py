from django.db.models import Sum, Q
from django.http import FileResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.listings.models import Listing
from apps.moderation.models import ListingReport
from apps.accounts.trust import calculate_user_trust_score
from apps.searches.alerts import notify_saved_search_matches_for_listing

from datetime import timedelta
from django.utils import timezone

from .permissions import IsAdministrator, IsAdminOrModerator
from .backups import (
    BackupBusyError,
    BackupError,
    BackupNotFoundError,
    create_backup,
    get_backup_path,
    list_backups,
    restore_backup,
)

from apps.payments.models import Payment, PromotionPackage

from apps.reviews.models import SellerReview

from apps.chats.models import ChatReport, ChatBlock

from .serializers import (
    AdminUserSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    AdminListingSerializer,
    AdminListingDetailSerializer,
    AdminListingUpdateSerializer,
    ListingRejectSerializer,
    UserBanSerializer,
    FeatureListingSerializer,
    AdminPaymentSerializer,
    AdminMarkPaymentPaidSerializer,
    AdminMarkPaymentFailedSerializer,
    AdminPromotionPackageSerializer,
    AdminDashboardSerializer,
    AdminCancelPaymentSerializer,
    AdminSellerReviewSerializer,
    AdminChatReportSerializer,
    ResolveChatReportSerializer,
    AdminChatBlockSerializer,
)

from apps.notifications.services import (
    create_listing_approved_notification,
    create_listing_rejected_notification,
    create_payment_paid_notification,
    create_payment_failed_notification,
)


def _backup_actor(user):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
    }


class AdminBackupListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request):
        backups = list_backups()
        return Response(
            {"count": len(backups), "results": backups},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        try:
            backup = create_backup(created_by=_backup_actor(request.user))
        except BackupBusyError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except BackupError:
            return Response(
                {"detail": "The database backup could not be created."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Database backup created successfully.", "backup": backup},
            status=status.HTTP_201_CREATED,
        )


class AdminBackupDownloadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request, filename):
        try:
            path = get_backup_path(filename)
        except BackupNotFoundError as error:
            return Response({"detail": str(error)}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename=path.name,
            content_type="application/octet-stream",
        )


class AdminBackupRestoreAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def post(self, request, filename):
        if request.data.get("confirmation") != "RESTORE":
            return Response(
                {"detail": 'Enter "RESTORE" to confirm this operation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = restore_backup(
                filename,
                restored_by=_backup_actor(request.user),
            )
        except BackupNotFoundError as error:
            return Response({"detail": str(error)}, status=status.HTTP_404_NOT_FOUND)
        except BackupBusyError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except BackupError:
            return Response(
                {
                    "detail": (
                        "The restore operation failed. A safety backup was created "
                        "before restoration was attempted."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Database restored successfully.",
                **result,
            },
            status=status.HTTP_200_OK,
        )

class AdminDashboardAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get(self, request):
        users = User.objects.all()
        listings = Listing.objects.exclude(status=Listing.STATUS_DELETED)
        reports = ListingReport.objects.all()
        payments = Payment.objects.all()

        paid_payments = payments.filter(status=Payment.STATUS_PAID)

        now = timezone.now()
        today = now.date()
        week_start = today - timezone.timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        today_paid = paid_payments.filter(
            paid_at__date=today,
        )

        this_week_paid = paid_payments.filter(
            paid_at__date__gte=week_start,
        )

        this_month_paid = paid_payments.filter(
            paid_at__date__gte=month_start,
        )

        total_revenue = paid_payments.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        featured_listing_revenue = paid_payments.filter(
            purpose=Payment.PURPOSE_FEATURED_LISTING,
        ).aggregate(
            total=Sum("amount"),
        )["total"] or 0

        boost_listing_revenue = paid_payments.filter(
            purpose=Payment.PURPOSE_BOOST_LISTING,
        ).aggregate(
            total=Sum("amount"),
        )["total"] or 0

        today_revenue = today_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        this_week_revenue = this_week_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        this_month_revenue = this_month_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        data = {
            "total_users": users.count(),
            "normal_users": users.filter(role=User.ROLE_USER).count(),
            "admin_users": users.filter(role=User.ROLE_ADMIN).count(),
            "moderator_users": users.filter(role=User.ROLE_MODERATOR).count(),
            "banned_users": users.filter(is_banned=True).count(),

            "total_listings": listings.count(),
            "active_listings": listings.filter(
                status=Listing.STATUS_ACTIVE,
            ).count(),
            
            "pending_listings": listings.filter(
                status=Listing.STATUS_PENDING,
            ).count(),
            "rejected_listings": listings.filter(
                status=Listing.STATUS_REJECTED,
            ).count(),
            "sold_listings": listings.filter(
                status=Listing.STATUS_SOLD,
            ).count(),
            "expired_listings": listings.filter(
                status=Listing.STATUS_EXPIRED,
            ).count(),
            "unavailable_listings": listings.filter(
                status=Listing.STATUS_UNAVAILABLE,
            ).count(),

            "total_reports": reports.count(),
            "unresolved_reports": reports.filter(
                is_resolved=False,
            ).count(),
            "resolved_reports": reports.filter(
                is_resolved=True,
            ).count(),

            "total_payments": payments.count(),
            "pending_payments": payments.filter(
                status=Payment.STATUS_PENDING,
            ).count(),
            "paid_payments": payments.filter(
                status=Payment.STATUS_PAID,
            ).count(),
            "failed_payments": payments.filter(
                status=Payment.STATUS_FAILED,
            ).count(),

            "total_revenue": total_revenue,
            "featured_listing_revenue": featured_listing_revenue,
            "boost_listing_revenue": boost_listing_revenue,

            "today_revenue": today_revenue,
            "this_week_revenue": this_week_revenue,
            "this_month_revenue": this_month_revenue,

            "today_paid_payments": today_paid.count(),
            "this_week_paid_payments": this_week_paid.count(),
            "this_month_paid_payments": this_month_paid.count(),
        }

        serializer = AdminDashboardSerializer(data)

        return Response(serializer.data, status=status.HTTP_200_OK)
    


class PendingListingListAPIView(generics.ListAPIView):
    serializer_class = AdminListingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            Listing.objects
            .filter(status=Listing.STATUS_PENDING)
            .select_related(
                "seller",
                "category",
                "category__parent",
                "city",
                "city__region",
            )
            .prefetch_related("images")
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        seller = self.request.query_params.get("seller")
        category = self.request.query_params.get("category")
        city = self.request.query_params.get("city")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(seller__full_name__icontains=search)
                | Q(seller__phone__icontains=search)
            )

        if seller:
            queryset = queryset.filter(seller_id=seller)

        if category:
            queryset = queryset.filter(
                Q(category__slug=category)
                | Q(category__parent__slug=category)
            )

        if city:
            queryset = queryset.filter(city__slug=city)

        return queryset.distinct()


class AdminListingListAPIView(generics.ListAPIView):
    serializer_class = AdminListingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            Listing.objects
            .exclude(status=Listing.STATUS_DELETED)
            .select_related(
                "seller",
                "category",
                "category__parent",
                "city",
                "city__region",
            )
            .prefetch_related("images")
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        status_param = self.request.query_params.get("status")
        seller = self.request.query_params.get("seller")
        category = self.request.query_params.get("category")
        city = self.request.query_params.get("city")
        is_featured = self.request.query_params.get("is_featured")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(seller__full_name__icontains=search)
                | Q(seller__phone__icontains=search)
            )

        if status_param:
            queryset = queryset.filter(status=status_param)

        if seller:
            queryset = queryset.filter(seller_id=seller)

        if category:
            queryset = queryset.filter(
                Q(category__slug=category)
                | Q(category__parent__slug=category)
            )

        if city:
            queryset = queryset.filter(city__slug=city)

        if is_featured == "true":
            queryset = queryset.filter(is_featured=True)

        if is_featured == "false":
            queryset = queryset.filter(is_featured=False)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()


class AdminListingDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return AdminListingUpdateSerializer

        return AdminListingDetailSerializer

    def get_queryset(self):
        return (
            Listing.objects
            .select_related(
                "seller",
                "seller__profile",
                "category",
                "category__parent",
                "city",
                "city__region",
            )
            .prefetch_related(
                "images",
                "attributes",
                "attributes__category_filter",
                "reports",
            )
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        listing = self.get_object()

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "Deleted listings cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            listing,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        listing.refresh_from_db()

        return Response(
            AdminListingDetailSerializer(
                listing,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

class ApproveListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.rejection_reason = ""
        listing.save(update_fields=["status", "rejection_reason", "updated_at"])

        create_listing_approved_notification(listing)
        calculate_user_trust_score(listing.seller)
        notify_saved_search_matches_for_listing(listing)

        return Response(
            {
                "message": "Listing approved successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class RejectListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ListingRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing.status = Listing.STATUS_REJECTED
        listing.rejection_reason = serializer.validated_data["rejection_reason"]
        listing.is_featured = False
        listing.featured_until = None
        listing.save(
            update_fields=[
                "status",
                "rejection_reason",
                "is_featured",
                "featured_until",
                "updated_at",
            ]
        )

        create_listing_rejected_notification(listing)
        calculate_user_trust_score(listing.seller)

        return Response(
            {
                "message": "Listing rejected successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )

class FeatureListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FeatureListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if listing.status != Listing.STATUS_ACTIVE:
            return Response(
                {"detail": "Only approved active listings can be featured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days = serializer.validated_data["days"]

        listing.is_featured = True
        listing.featured_until = timezone.now() + timedelta(days=days)
        listing.save(update_fields=["is_featured", "featured_until", "updated_at"])

        return Response(
            {
                "message": "Listing featured successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "This listing has already been deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_DELETED
        listing.is_featured = False
        listing.featured_until = None
        listing.save(
            update_fields=[
                "status",
                "is_featured",
                "featured_until",
                "updated_at",
            ]
        )
        calculate_user_trust_score(listing.seller)

        return Response(
            {
                "message": "Listing deleted successfully.",
                "listing": AdminListingDetailSerializer(
                    listing,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class UnfeatureListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing.is_featured = False
        listing.featured_until = None
        listing.save(update_fields=["is_featured", "featured_until", "updated_at"])

        return Response(
            {
                "message": "Listing unfeatured successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListAPIView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = User.objects.select_related("profile").order_by("-date_joined")

        search = self.request.query_params.get("search")
        role = self.request.query_params.get("role")
        is_banned = self.request.query_params.get("is_banned")
        is_verified = self.request.query_params.get("is_verified")

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        if role:
            queryset = queryset.filter(role=role)

        if is_banned == "true":
            queryset = queryset.filter(is_banned=True)

        if is_banned == "false":
            queryset = queryset.filter(is_banned=False)

        if is_verified == "true":
            queryset = queryset.filter(is_verified=True)

        if is_verified == "false":
            queryset = queryset.filter(is_verified=False)

        return queryset


class AdminUserDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AdminUserDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_queryset(self):
        return User.objects.select_related("profile")

    def patch(self, request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.role == User.ROLE_ADMIN
        ):
            return Response(
                {"detail": "Only administrators can edit user accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = self.get_object()

        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {"detail": "Only a superuser can edit another superuser account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AdminUserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        calculate_user_trust_score(user)

        return Response(
            {
                "message": "User account updated successfully.",
                "user": AdminUserDetailSerializer(
                    user,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )
    

class BanUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user == request.user:
            return Response(
                {"detail": "You cannot ban your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requester_is_admin = (
            request.user.is_superuser
            or request.user.role == User.ROLE_ADMIN
        )

        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {"detail": "Only a superuser can restrict a superuser account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            user.role in {User.ROLE_ADMIN, User.ROLE_MODERATOR}
            and not requester_is_admin
        ):
            return Response(
                {"detail": "Only administrators can restrict staff accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            user.role == User.ROLE_ADMIN
            and user.is_active
            and not user.is_banned
            and User.objects.filter(
                role=User.ROLE_ADMIN,
                is_active=True,
                is_banned=False,
            ).count() <= 1
        ):
            return Response(
                {"detail": "The platform must retain at least one active administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserBanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.is_banned = True
        user.banned_reason = serializer.validated_data.get("banned_reason", "")
        user.save(update_fields=["is_banned", "banned_reason", "updated_at"])
        calculate_user_trust_score(user)

        return Response(
            {
                "message": "User banned successfully.",
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class UnbanUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            user.is_superuser
            and not request.user.is_superuser
        ):
            return Response(
                {"detail": "Only a superuser can restore a superuser account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            user.role in {User.ROLE_ADMIN, User.ROLE_MODERATOR}
            and not (
                request.user.is_superuser
                or request.user.role == User.ROLE_ADMIN
            )
        ):
            return Response(
                {"detail": "Only administrators can restore staff accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_banned = False
        user.banned_reason = ""
        user.save(update_fields=["is_banned", "banned_reason", "updated_at"])

        return Response(
            {
                "message": "User unbanned successfully.",
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

class AdminPaymentListAPIView(generics.ListAPIView):
    serializer_class = AdminPaymentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            Payment.objects
            .select_related("user", "listing", "package")
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        status_param = self.request.query_params.get("status")
        purpose = self.request.query_params.get("purpose")
        user = self.request.query_params.get("user")
        listing = self.request.query_params.get("listing")
        payment_method = self.request.query_params.get("payment_method")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(provider_reference__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(user__phone__icontains=search)
                | Q(user__email__icontains=search)
                | Q(listing__title__icontains=search)
            )

        if status_param:
            queryset = queryset.filter(status=status_param)

        if purpose:
            queryset = queryset.filter(purpose=purpose)

        if user:
            queryset = queryset.filter(user_id=user)

        if listing:
            queryset = queryset.filter(listing_id=listing)

        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()

class AdminMarkPaymentPaidAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            payment = Payment.objects.select_related(
                "listing",
                "package",
                "user",
            ).get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status == Payment.STATUS_PAID:
            return Response(
                {"detail": "This payment is already marked as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status == Payment.STATUS_CANCELLED:
            return Response(
                {"detail": "Cancelled payments cannot be marked as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminMarkPaymentPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment.status = Payment.STATUS_PAID
        payment.provider_reference = serializer.validated_data.get(
            "provider_reference",
            "",
        )
        payment.notes = serializer.validated_data.get("notes", "")
        payment.paid_at = timezone.now()
        payment.save(
            update_fields=[
                "status",
                "provider_reference",
                "notes",
                "paid_at",
                "updated_at",
            ]
        )

        if (
            payment.purpose == Payment.PURPOSE_FEATURED_LISTING
            and payment.listing is not None
        ):
            duration_days = 7

            if payment.package:
                duration_days = payment.package.duration_days

            payment.listing.is_featured = True
            payment.listing.featured_until = timezone.now() + timedelta(
                days=duration_days,
            )
            payment.listing.save(
                update_fields=[
                    "is_featured",
                    "featured_until",
                    "updated_at",
                ]
            )

        create_payment_paid_notification(payment)

        return Response(
            {
                "message": "Payment marked as paid successfully.",
                "payment": AdminPaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )





class AdminMarkPaymentFailedAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            payment = Payment.objects.select_related(
                "user",
                "listing",
            ).get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status == Payment.STATUS_PAID:
            return Response(
                {"detail": "Paid payments cannot be marked as failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status == Payment.STATUS_CANCELLED:
            return Response(
                {"detail": "Cancelled payments cannot be marked as failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminMarkPaymentFailedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment.status = Payment.STATUS_FAILED
        payment.notes = serializer.validated_data.get("notes", "")
        payment.save(update_fields=["status", "notes", "updated_at"])

        create_payment_failed_notification(payment)

        return Response(
            {
                "message": "Payment marked as failed.",
                "payment": AdminPaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )





class AdminCancelPaymentAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            payment = Payment.objects.select_related(
                "user",
                "listing",
            ).get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status == Payment.STATUS_PAID:
            return Response(
                {"detail": "Paid payments cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status == Payment.STATUS_CANCELLED:
            return Response(
                {"detail": "This payment is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminCancelPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment.status = Payment.STATUS_CANCELLED
        payment.notes = serializer.validated_data.get("notes", "")
        payment.save(update_fields=["status", "notes", "updated_at"])

        return Response(
            {
                "message": "Payment cancelled successfully.",
                "payment": AdminPaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        ) 
    
    

class AdminPromotionPackageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AdminPromotionPackageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = PromotionPackage.objects.all().order_by(
            "sort_order",
            "price",
            "name",
        )

        package_type = self.request.query_params.get("package_type")
        is_active = self.request.query_params.get("is_active")

        if package_type:
            queryset = queryset.filter(package_type=package_type)

        if is_active == "true":
            queryset = queryset.filter(is_active=True)

        if is_active == "false":
            queryset = queryset.filter(is_active=False)

        return queryset


class AdminPromotionPackageDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminPromotionPackageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    queryset = PromotionPackage.objects.all()



class AdminSellerReviewListAPIView(generics.ListAPIView):
    serializer_class = AdminSellerReviewSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            SellerReview.objects
            .select_related(
                "reviewer",
                "seller",
                "listing",
            )
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        rating = self.request.query_params.get("rating")
        seller = self.request.query_params.get("seller")
        reviewer = self.request.query_params.get("reviewer")
        listing = self.request.query_params.get("listing")
        is_visible = self.request.query_params.get("is_visible")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(comment__icontains=search)
                | Q(seller__full_name__icontains=search)
                | Q(seller__phone__icontains=search)
                | Q(reviewer__full_name__icontains=search)
                | Q(reviewer__phone__icontains=search)
                | Q(listing__title__icontains=search)
            )

        if rating:
            queryset = queryset.filter(rating=rating)

        if seller:
            queryset = queryset.filter(seller_id=seller)

        if reviewer:
            queryset = queryset.filter(reviewer_id=reviewer)

        if listing:
            queryset = queryset.filter(listing_id=listing)

        if is_visible == "true":
            queryset = queryset.filter(is_visible=True)

        if is_visible == "false":
            queryset = queryset.filter(is_visible=False)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()


class AdminHideSellerReviewAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            review = SellerReview.objects.select_related("seller").get(pk=pk)
        except SellerReview.DoesNotExist:
            return Response(
                {"detail": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not review.is_visible:
            return Response(
                {"detail": "This review is already hidden."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.is_visible = False
        review.save(update_fields=["is_visible", "updated_at"])

        calculate_user_trust_score(review.seller)

        return Response(
            {
                "message": "Review hidden successfully.",
                "review": AdminSellerReviewSerializer(review).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminShowSellerReviewAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            review = SellerReview.objects.select_related("seller").get(pk=pk)
        except SellerReview.DoesNotExist:
            return Response(
                {"detail": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if review.is_visible:
            return Response(
                {"detail": "This review is already visible."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.is_visible = True
        review.save(update_fields=["is_visible", "updated_at"])

        calculate_user_trust_score(review.seller)

        return Response(
            {
                "message": "Review shown successfully.",
                "review": AdminSellerReviewSerializer(review).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminChatReportListAPIView(generics.ListAPIView):
    serializer_class = AdminChatReportSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            ChatReport.objects
            .select_related(
                "thread",
                "thread__listing",
                "reporter",
                "reported_user",
                "resolved_by",
            )
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        reason = self.request.query_params.get("reason")
        is_resolved = self.request.query_params.get("is_resolved")
        reporter = self.request.query_params.get("reporter")
        reported_user = self.request.query_params.get("reported_user")
        thread = self.request.query_params.get("thread")
        listing = self.request.query_params.get("listing")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(description__icontains=search)
                | Q(reporter__full_name__icontains=search)
                | Q(reporter__phone__icontains=search)
                | Q(reported_user__full_name__icontains=search)
                | Q(reported_user__phone__icontains=search)
                | Q(thread__listing__title__icontains=search)
            )

        if reason:
            queryset = queryset.filter(reason=reason)

        if is_resolved == "true":
            queryset = queryset.filter(is_resolved=True)

        if is_resolved == "false":
            queryset = queryset.filter(is_resolved=False)

        if reporter:
            queryset = queryset.filter(reporter_id=reporter)

        if reported_user:
            queryset = queryset.filter(reported_user_id=reported_user)

        if thread:
            queryset = queryset.filter(thread_id=thread)

        if listing:
            queryset = queryset.filter(thread__listing_id=listing)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()


class AdminChatReportDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AdminChatReportSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    queryset = (
        ChatReport.objects
        .select_related(
            "thread",
            "thread__listing",
            "reporter",
            "reported_user",
            "resolved_by",
        )
    )


class ResolveChatReportAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            report = ChatReport.objects.select_related(
                "thread",
                "thread__listing",
                "reporter",
                "reported_user",
                "resolved_by",
            ).get(pk=pk)
        except ChatReport.DoesNotExist:
            return Response(
                {"detail": "Chat report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if report.is_resolved:
            return Response(
                {"detail": "This chat report is already resolved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResolveChatReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "")

        if note:
            if report.description:
                report.description = f"{report.description}\n\nAdmin note: {note}"
            else:
                report.description = f"Admin note: {note}"

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()

        report.save(
            update_fields=[
                "description",
                "is_resolved",
                "resolved_by",
                "resolved_at",
            ]
        )

        return Response(
            {
                "message": "Chat report resolved successfully.",
                "report": AdminChatReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminChatBlockListAPIView(generics.ListAPIView):
    serializer_class = AdminChatBlockSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            ChatBlock.objects
            .select_related(
                "blocker",
                "blocked_user",
                "thread",
                "thread__listing",
            )
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        blocker = self.request.query_params.get("blocker")
        blocked_user = self.request.query_params.get("blocked_user")
        thread = self.request.query_params.get("thread")
        listing = self.request.query_params.get("listing")
        is_active = self.request.query_params.get("is_active")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(reason__icontains=search)
                | Q(blocker__full_name__icontains=search)
                | Q(blocker__phone__icontains=search)
                | Q(blocked_user__full_name__icontains=search)
                | Q(blocked_user__phone__icontains=search)
                | Q(thread__listing__title__icontains=search)
            )

        if blocker:
            queryset = queryset.filter(blocker_id=blocker)

        if blocked_user:
            queryset = queryset.filter(blocked_user_id=blocked_user)

        if thread:
            queryset = queryset.filter(thread_id=thread)

        if listing:
            queryset = queryset.filter(thread__listing_id=listing)

        if is_active == "true":
            queryset = queryset.filter(is_active=True)

        if is_active == "false":
            queryset = queryset.filter(is_active=False)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()
