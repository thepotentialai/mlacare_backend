from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    message = "Accès réservé aux patients."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'patient'


class IsAgent(BasePermission):
    message = "Accès réservé aux agents."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agent'


class IsAdmin(BasePermission):
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == 'admin' or request.user.is_staff
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_staff:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
