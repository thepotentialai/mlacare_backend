"""Création centralisée des notifications applicatives."""

from django.db.models import Q
from django.utils import timezone

from accounts.models import User

from .models import Notification

AGENT_RESUBMIT_TITLE = 'Candidature agent resoumise'


def _agent_resubmit_tag(agent_profile_id: int) -> str:
    return f'[agent_id={agent_profile_id}]'


def notify_admins_agent_resubmitted(profile) -> None:
    """Informe les administrateurs qu'un agent a resoumis sa candidature.

    Une seule alerte non lue par agent est conservée : une nouvelle resoumission
    met à jour l'alerte existante au lieu d'en créer une autre.
    """
    agent_tag = _agent_resubmit_tag(profile.id)
    message = (
        f'{profile.display_name} ({profile.user.email}) a resoumis sa candidature '
        f'après corrections. {agent_tag}'
    )
    admin_users = User.objects.filter(
        Q(role='admin') | Q(is_staff=True),
        is_active=True,
    )

    for admin in admin_users:
        existing = Notification.objects.filter(
            user=admin,
            title=AGENT_RESUBMIT_TITLE,
            is_read=False,
            message__contains=agent_tag,
        ).first()
        if existing:
            Notification.objects.filter(pk=existing.pk).update(
                message=message,
                created_at=timezone.now(),
            )
        else:
            Notification.objects.create(
                user=admin,
                title=AGENT_RESUBMIT_TITLE,
                message=message,
                type='alert',
            )
