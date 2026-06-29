import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

REJECTION_TYPE_REVISION = 'revision'
REJECTION_TYPE_DEFINITIVE = 'definitive'


def _send_agent_revision_required_email(user, profile, reason: str) -> None:
    subject = 'MLACare — Corrections demandées sur votre candidature agent'
    message = (
        f"Bonjour {profile.display_name},\n\n"
        f"Votre candidature agent MLACare nécessite des corrections avant validation.\n\n"
        f"Motif / éléments à corriger :\n{reason}\n\n"
        f"Connectez-vous à votre espace agent pour mettre à jour vos informations "
        f"ou documents, puis resoumettez votre candidature.\n\n"
        f"Pour toute question, contactez le support MLACare.\n\n"
        f"Cordialement,\nL'équipe MLACare"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def _send_agent_definitive_rejection_email(user, profile, reason: str) -> None:
    subject = 'MLACare — Candidature agent non retenue'
    message = (
        f"Bonjour {profile.display_name},\n\n"
        f"Nous vous informons que votre candidature en tant qu'agent MLACare "
        f"a été définitivement refusée.\n\n"
        f"Motif :\n{reason}\n\n"
        f"Vous ne pouvez plus soumettre de candidature avec ce compte.\n"
        f"Pour toute question, contactez le support MLACare.\n\n"
        f"Cordialement,\nL'équipe MLACare"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_agent_rejection_email_safe(user, profile, reason: str, *, rejection_type: str) -> bool:
    try:
        if rejection_type == REJECTION_TYPE_REVISION:
            _send_agent_revision_required_email(user, profile, reason)
        else:
            _send_agent_definitive_rejection_email(user, profile, reason)
        return True
    except Exception:
        logger.exception(
            "Agent rejection email failed for user_id=%s (type=%s)",
            user.id,
            rejection_type,
        )
        return False
