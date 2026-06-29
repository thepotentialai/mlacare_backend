from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    message = "Accès réservé aux patients."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'patient'


class IsAgent(BasePermission):
    message = "Accès réservé aux agents."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agent'


class IsApprovedAgent(BasePermission):
    message = "Votre compte agent n'est pas approuvé."

    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.role != 'agent':
            return False
        profile = getattr(request.user, 'agent_profile', None)
        return bool(profile and profile.approval_status == 'approved')


class IsApprovedAgentIfAgent(BasePermission):
    """Patients et admins passent ; les agents doivent être approuvés."""

    message = "Votre compte agent n'est pas approuvé."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role != 'agent':
            return True
        profile = getattr(request.user, 'agent_profile', None)
        return bool(profile and profile.approval_status == 'approved')


class IsApprovedOrRevisionAgent(BasePermission):
    """Agent approuvé ou en attente de corrections (modification profil / documents)."""

    message = "Votre compte agent n'est pas autorisé à effectuer cette action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.role != 'agent':
            return False
        profile = getattr(request.user, 'agent_profile', None)
        return bool(profile and profile.approval_status in ('approved', 'revision_required'))


class IsRevisionRequiredAgent(BasePermission):
    message = "Aucune correction n'est demandée sur votre candidature."

    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.role != 'agent':
            return False
        profile = getattr(request.user, 'agent_profile', None)
        return bool(profile and profile.approval_status == 'revision_required')


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
