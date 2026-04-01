import logging
from datetime import timedelta

from django.db.models import Count, Q

from agents.models import AgentProfile

logger = logging.getLogger(__name__)

DEFAULT_VISIT_TIME = '09:00:00'


def assign_agent_to_visit(visit):
    """
    Assigne un agent approuvé, disponible, dont la zone de couverture inclut
    la zone de résidence du patient. En cas d'égalité, privilégie la charge la plus faible.
    Si le patient a déjà un agent assigné, on l'utilise directement.
    """
    patient = visit.patient

    # Prefer the already-assigned agent for this patient
    if patient.assigned_agent_id:
        visit.agent = patient.assigned_agent
        visit.save(update_fields=['agent'])
        return

    zone = patient.zone
    if not zone:
        return

    candidates = (
        AgentProfile.objects.filter(
            approval_status='approved',
            is_available=True,
            coverage_zones=zone,
        )
        .annotate(
            active_visits=Count(
                'visits',
                filter=Q(
                    visits__status__in=['pending', 'confirmed', 'in_progress'],
                ),
            ),
        )
        .order_by('active_visits', 'id')
    )
    agent = candidates.first()
    if agent:
        visit.agent = agent
        visit.save(update_fields=['agent'])


def generate_visits_for_subscription(subscription):
    """
    Génère les visites planifiées pour un abonnement donné.

    - Lit plan.visits_per_month et la période start_date / end_date.
    - Répartit N visites uniformément sur la période.
    - Crée chaque Visit avec status='pending', subscription=sub, visit_number=i.
    - Assigne l'agent du patient directement (via assign_agent_to_visit).
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

    # Assign agent to each created visit
    created_visits = Visit.objects.filter(subscription=subscription).order_by('visit_number')
    for visit in created_visits:
        try:
            assign_agent_to_visit(visit)
        except Exception:
            logger.exception("Erreur lors de l'assignation de l'agent à la visite #%s.", visit.id)
