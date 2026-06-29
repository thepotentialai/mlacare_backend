"""Transitions d'approbation agent (approve / reject / resubmit) centralisées."""

from django.db import transaction
from django.utils import timezone

from .emails import (
    REJECTION_TYPE_DEFINITIVE,
    REJECTION_TYPE_REVISION,
    send_agent_rejection_email_safe,
)
from .zone_approval import apply_pending_zones_to_approved, clear_pending_zones


@transaction.atomic
def reject_agent(profile, *, by_user, reason: str, rejection_type: str = REJECTION_TYPE_DEFINITIVE) -> None:
    reason = reason.strip()
    if rejection_type == REJECTION_TYPE_REVISION:
        profile.approval_status = 'revision_required'
    else:
        profile.approval_status = 'rejected'
        clear_pending_zones(profile)

    profile.is_available = False
    profile.rejection_reason = reason
    profile.revision_notes = ''
    profile.rejected_at = timezone.now()
    profile.rejected_by = by_user
    profile.save(
        update_fields=[
            'approval_status',
            'is_available',
            'rejection_reason',
            'revision_notes',
            'rejected_at',
            'rejected_by',
            'updated_at',
        ]
    )
    send_agent_rejection_email_safe(
        profile.user,
        profile,
        profile.rejection_reason,
        rejection_type=rejection_type,
    )


@transaction.atomic
def approve_agent(profile, *, by_user=None) -> None:
    profile.approval_status = 'approved'
    profile.rejection_reason = ''
    profile.revision_notes = ''
    profile.rejected_at = None
    profile.rejected_by = None
    profile.save(
        update_fields=[
            'approval_status',
            'rejection_reason',
            'revision_notes',
            'rejected_at',
            'rejected_by',
            'updated_at',
        ]
    )
    apply_pending_zones_to_approved(profile)


@transaction.atomic
def resubmit_agent_application(profile) -> None:
    if profile.approval_status != 'revision_required':
        raise ValueError("Seuls les agents en attente de corrections peuvent resoumettre.")

    profile.approval_status = 'pending'
    profile.rejection_reason = ''
    profile.rejected_at = None
    profile.rejected_by = None
    profile.save(
        update_fields=[
            'approval_status',
            'rejection_reason',
            'rejected_at',
            'rejected_by',
            'updated_at',
        ]
    )

    from notifications.services import notify_admins_agent_resubmitted

    notify_admins_agent_resubmitted(profile)
