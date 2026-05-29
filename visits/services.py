import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q

from agents.models import AgentProfile

logger = logging.getLogger(__name__)

DEFAULT_VISIT_TIME = '09:00:00'
ACTIVE_VISIT_STATUSES = ['pending', 'confirmed', 'in_progress']


def assign_agent_to_visit(visit):
    """
    Assigne dynamiquement un agent disponible à une visite non assignée.

    Règles:
    - ne jamais réassigner une visite déjà assignée
    - priorité aux agents de la zone du patient
    - fallback global sur agents disponibles si la zone n'a aucun candidat
    - choix de l'agent avec charge active minimale
    - comportement idempotent et sûr en concurrence
    """
    if visit.agent_id:
        return None

    with transaction.atomic():
        locked_visit = (
            type(visit).objects.select_for_update()
            .get(pk=visit.pk)
        )
        if locked_visit.agent_id:
            return None

        patient_zone = locked_visit.patient.zone
        base_candidates = AgentProfile.objects.filter(
            approval_status='approved',
            is_available=True,
        ).annotate(
            active_visits=Count(
                'visits',
                filter=Q(visits__status__in=ACTIVE_VISIT_STATUSES),
            ),
        )

        agent = None
        if patient_zone:
            agent = (
                base_candidates.filter(coverage_zones=patient_zone)
                .order_by('active_visits', 'id')
                .first()
            )

        if agent is None:
            agent = base_candidates.order_by('active_visits', 'id').first()

        if agent is None:
            return None

        updated = type(visit).objects.filter(pk=locked_visit.pk, agent__isnull=True).update(agent=agent)
        if updated:
            visit.agent_id = agent.id
            return agent
        return None


def generate_visits_for_subscription(subscription):
    """
    Génère les visites planifiées pour un abonnement donné.

    - Lit plan.visits_per_month et la période start_date / end_date.
    - Répartit N visites uniformément sur la période.
    - Crée chaque Visit avec status='pending', subscription=sub, visit_number=i.
    - Laisse les visites sans agent (assignation just-in-time via commande périodique).
    - Ignore si des visites liées à cet abonnement existent déjà (idempotent).
    """
    from .models import Visit  # local import to avoid circular deps

    if subscription.visits.exists():
        logger.info(
            "Visites déjà générées pour l'abonnement #%s — skip.",
            subscription.id,
        )
        return

    patient = subscription.patient
    plan = subscription.plan
    n = plan.visits_per_month

    if n <= 0:
        return

    start = subscription.start_date
    end = subscription.end_date
    total_days = (end - start).days

    # Spread visits evenly; minimum 1-day gap
    if n == 1:
        offsets = [total_days // 2]
    else:
        step = total_days / n
        offsets = [int(step * i + step / 2) for i in range(n)]

    address = f"{patient.address}, {patient.city}" if patient.address else patient.city or ""

    visits = []
    for idx, offset in enumerate(offsets, start=1):
        visit_date = start + timedelta(days=offset)
        visit = Visit(
            patient=patient,
            subscription=subscription,
            visit_number=idx,
            scheduled_date=visit_date,
            scheduled_time=DEFAULT_VISIT_TIME,
            status='pending',
            address=address,
        )
        visits.append(visit)

    Visit.objects.bulk_create(visits)
    logger.info(
        "%d visites générées pour l'abonnement #%s (patient %s, plan '%s').",
        len(visits),
        subscription.id,
        patient.id,
        plan.name,
    )

