from rest_framework import permissions


class IsNotBanned(permissions.BasePermission):
    message = "Your account has been restricted. Please contact support."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return not user.is_banned


class IsVerifiedUser(permissions.BasePermission):
    message = "Please verify your account before performing this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.is_verified


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        owner = getattr(obj, "user", None) or getattr(obj, "seller", None)

        return owner == request.user