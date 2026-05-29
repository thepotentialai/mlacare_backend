"""Applique ou efface les zones soumises par l'agent (en attente de validation admin)."""

from django.db import transaction


@transaction.atomic
def apply_pending_zones_to_approved(profile):
    """
    Copie pending_residence_zone / pending_coverage_zones vers les champs opérationnels
    (matching), puis vide les champs « en attente ».
    """
    has_pending = profile.pending_residence_zone_id is not None or profile.pending_coverage_zones.exists()
    if not has_pending:
        return

    profile.residence_zone = profile.pending_residence_zone
    ids = list(profile.pending_coverage_zones.values_list('pk', flat=True))
    if ids:
        profile.coverage_zones.set(ids)
    elif profile.pending_residence_zone_id:
        profile.coverage_zones.set([profile.pending_residence_zone_id])
    else:
        profile.coverage_zones.clear()

    profile.pending_residence_zone = None
    profile.pending_coverage_zones.clear()
    profile.save(
        update_fields=[
            'residence_zone',
            'pending_residence_zone',
            'updated_at',
        ]
    )


@transaction.atomic
def clear_pending_zones(profile):
    profile.pending_residence_zone = None
    profile.pending_coverage_zones.clear()
    profile.save(update_fields=['pending_residence_zone', 'updated_at'])


@transaction.atomic
def apply_selected_pending_zones(profile, approve_residence, approved_coverage_zone_ids):
    """
    Applique partiellement une demande de zones.

    - approve_residence=True : copie pending_residence_zone vers residence_zone.
    - approved_coverage_zone_ids : sous-ensemble des pending_coverage_zones à conserver.
    - Les zones pending sont toujours vidées après traitement.
    """
    pending_cov_ids = set(profile.pending_coverage_zones.values_list('pk', flat=True))
    approved_cov_ids = [zid for zid in approved_coverage_zone_ids if zid in pending_cov_ids]

    if approve_residence and profile.pending_residence_zone_id is not None:
        profile.residence_zone = profile.pending_residence_zone

    if approved_cov_ids:
        profile.coverage_zones.set(approved_cov_ids)
    elif approve_residence and profile.pending_residence_zone_id is not None:
        # Cohérence avec la logique historique: au moins la résidence approuvée en couverture.
        profile.coverage_zones.set([profile.pending_residence_zone_id])
    else:
        profile.coverage_zones.clear()

    profile.pending_residence_zone = None
    profile.pending_coverage_zones.clear()
    profile.save(update_fields=['residence_zone', 'pending_residence_zone', 'updated_at'])
