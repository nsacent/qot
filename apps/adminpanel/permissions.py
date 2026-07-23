from rest_framework import permissions


class IsAdminOrModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.is_staff or user.role in ["admin", "moderator"]


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.is_superuser or (user.is_staff and user.role == "admin")
