import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_admin_setting(key, default):
    """Fetch a value from AdminSetting, falling back to default on any error."""
    try:
        from admin_api.models import AdminSetting
        return AdminSetting.objects.get(key=key).value
    except Exception:
        return default


def notify_agent(agent_id, message):
    """Push a real-time message to an agent via Django Channels."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"agent_{agent_id}",
            {"type": "assignment_notification", "message": message},
        )
        logger.debug(f"Notified agent {agent_id}: {message.get('type')}")
    except Exception as e:
        logger.error(f"Error notifying agent {agent_id}: {e}")


def notify_patient(patient_id, message):
    """Push a real-time message to a patient via Django Channels."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"patient_{patient_id}",
            {"type": "assignment_update", "message": message},
        )
        logger.debug(f"Notified patient {patient_id}: {message.get('type')}")
    except Exception as e:
        logger.error(f"Error notifying patient {patient_id}: {e}")


def _get_candidate_agents(patient):
    """
    Return an ordered list of AgentProfile IDs covering the patient's zone.

    Ordering priority:
      1. Agents whose residence_zone matches the patient's zone (closest familiarity)
      2. Then all other covering agents
      Within each group: more experienced first (experience_years DESC)

    Agents must be approved and not already processing another request.
    """
    from agents.models import AgentProfile

    if not patient.zone:
        return []

    base_qs = (
        AgentProfile.objects
        .filter(
            approval_status='approved',
            coverage_zones=patient.zone,
        )
        .exclude(assignment_requests__status='pending')
        .distinct()
    )

    same_zone_ids = list(
        base_qs.filter(residence_zone=patient.zone)
        .order_by('-experience_years')
        .values_list('id', flat=True)
    )
    other_zone_ids = list(
        base_qs.exclude(residence_zone=patient.zone)
        .order_by('-experience_years')
        .values_list('id', flat=True)
    )
    return same_zone_ids + other_zone_ids


def _schedule_retry(patient_profile_id, current_retry_count):
    """Schedule a delayed retry or give up after max_retries."""
    try:
        max_retries = int(_get_admin_setting('matching_max_retries', '3'))
        if current_retry_count >= max_retries:
            logger.warning(
                f"Patient {patient_profile_id}: max retries ({max_retries}) reached, giving up."
            )
            _notify_matching_failed(patient_profile_id)
            return

        delay_hours = int(_get_admin_setting('matching_retry_delay_hours', '6'))
        retry_patient_matching.apply_async(
            args=[patient_profile_id, current_retry_count + 1],
            countdown=delay_hours * 3600,
        )
        logger.info(
            f"Patient {patient_profile_id}: retry {current_retry_count + 1} scheduled in {delay_hours}h."
        )
    except Exception as e:
        logger.error(f"Error scheduling retry for patient {patient_profile_id}: {e}", exc_info=True)


def _notify_matching_failed(patient_profile_id):
    """Create an in-app notification and push a WS event when all retries are exhausted."""
    from notifications.models import Notification
    from patients.models import PatientProfile

    try:
        patient = PatientProfile.objects.select_related('user').get(id=patient_profile_id)
        Notification.objects.create(
            user=patient.user,
            title="Aucun agent disponible",
            message=(
                "Nous n'avons trouvé aucun agent disponible dans votre zone pour le moment. "
                "Notre équipe va vous contacter."
            ),
            type='alert',
        )
        notify_patient(patient.id, {
            "type": "matching_failed",
            "message": "Aucun agent disponible dans votre zone pour le moment.",
        })
    except Exception as e:
        logger.error(f"Error notifying patient {patient_profile_id} of matching failure: {e}")


# ─── Celery tasks ─────────────────────────────────────────────────────────────

@shared_task(bind=True, name='matching.start_patient_matching')
def start_patient_matching(self, patient_profile_id):
    """
    Entry-point task: find candidate agents and create an AssignmentQueue.
    Triggered immediately after a patient creates a subscription.
    """
    from matching.models import AssignmentQueue
    from patients.models import PatientProfile

    try:
        patient = PatientProfile.objects.select_related('zone', 'assigned_agent').get(
            id=patient_profile_id
        )

        if patient.assigned_agent_id is not None:
            logger.info(f"Patient {patient_profile_id} already has an assigned agent — skipping.")
            return

        # Don't create a second queue if one is still running
        if AssignmentQueue.objects.filter(patient=patient, status='pending').exists():
            logger.info(f"Patient {patient_profile_id} already has an active queue — skipping.")
            return

        agent_ids = _get_candidate_agents(patient)
        if not agent_ids:
            logger.warning(
                f"Patient {patient_profile_id}: no eligible agents in zone '{patient.zone}'."
            )
            _schedule_retry(patient_profile_id, 0)
            return

        queue = AssignmentQueue.objects.create(
            patient=patient,
            ordered_agent_ids=agent_ids,
            current_index=0,
            status='pending',
            retry_count=0,
        )
        logger.info(
            f"AssignmentQueue #{queue.id} created with {len(agent_ids)} candidates "
            f"for patient {patient_profile_id}."
        )
        send_to_next_agent.delay(queue.id)

    except PatientProfile.DoesNotExist:
        logger.error(f"PatientProfile {patient_profile_id} not found.")
    except Exception as e:
        logger.error(
            f"Error in start_patient_matching for patient {patient_profile_id}: {e}",
            exc_info=True,
        )


@shared_task(bind=True, name='matching.send_to_next_agent')
def send_to_next_agent(self, queue_id):
    """
    Send an AssignmentRequest to the next agent in the queue.
    Schedules a 6-hour timeout task and notifies both agent and patient.
    """
    from agents.models import AgentProfile
    from matching.models import AssignmentQueue, AssignmentRequest

    try:
        queue = AssignmentQueue.objects.select_related('patient__zone').get(id=queue_id)

        if queue.status != 'pending':
            logger.info(f"Queue #{queue_id} is {queue.status} — stopping.")
            return

        if queue.current_index >= len(queue.ordered_agent_ids):
            logger.info(f"Queue #{queue_id}: all candidates exhausted.")
            queue.status = 'failed'
            queue.save(update_fields=['status', 'updated_at'])
            _schedule_retry(queue.patient_id, queue.retry_count)
            return

        agent_id = queue.ordered_agent_ids[queue.current_index]

        # Skip if agent already has a pending request (state may have changed since queue was built)
        if AssignmentRequest.objects.filter(agent_id=agent_id, status='pending').exists():
            logger.info(f"Queue #{queue_id}: agent {agent_id} busy — advancing.")
            queue.current_index += 1
            queue.save(update_fields=['current_index', 'updated_at'])
            send_to_next_agent.delay(queue_id)
            return

        try:
            agent = AgentProfile.objects.get(id=agent_id)
        except AgentProfile.DoesNotExist:
            logger.warning(f"Queue #{queue_id}: agent {agent_id} not found — advancing.")
            queue.current_index += 1
            queue.save(update_fields=['current_index', 'updated_at'])
            send_to_next_agent.delay(queue_id)
            return

        patient = queue.patient
        timeout_hours = int(_get_admin_setting('assignment_request_timeout_hours', '6'))
        expires_at = timezone.now() + timedelta(hours=timeout_hours)

        req = AssignmentRequest.objects.create(
            queue=queue,
            patient=patient,
            agent=agent,
            status='pending',
            expires_at=expires_at,
        )

        # Schedule the expiry task at exactly expires_at
        timeout_task = handle_assignment_timeout.apply_async(
            args=[req.id],
            eta=expires_at,
        )
        req.celery_task_id = timeout_task.id
        req.save(update_fields=['celery_task_id'])

        # ── notify agent ──
        notify_agent(agent.id, {
            "type": "assignment_request",
            "request_id": req.id,
            "queue_id": queue.id,
            "patient_id": patient.id,
            "patient_name": patient.full_name,
            "patient_zone": patient.zone.name if patient.zone else "",
            "patient_city": patient.zone.city if patient.zone else "",
            "patient_address": patient.address,
            "health_notes": patient.health_notes,
            "expires_at": expires_at.isoformat(),
            "message": f"Nouvelle demande d'assignation pour {patient.full_name}",
        })

        # ── notify patient ──
        notify_patient(patient.id, {
            "type": "matching_in_progress",
            "queue_id": queue.id,
            "message": f"Demande envoyée à l'agent {agent.full_name}…",
        })

        logger.info(
            f"AssignmentRequest #{req.id} sent to agent {agent_id} "
            f"(expires {expires_at.isoformat()}) for patient {patient.id}."
        )

    except AssignmentQueue.DoesNotExist:
        logger.error(f"AssignmentQueue #{queue_id} not found.")
    except Exception as e:
        logger.error(f"Error in send_to_next_agent queue #{queue_id}: {e}", exc_info=True)


@shared_task(bind=True, name='matching.handle_assignment_timeout')
def handle_assignment_timeout(self, request_id):
    """
    Fires when an agent's 6-hour window expires without a response.
    Marks the request as expired and advances to the next candidate.
    """
    from matching.models import AssignmentRequest, AssignmentQueue

    try:
        req = AssignmentRequest.objects.select_related('queue', 'patient', 'agent').get(
            id=request_id
        )

        if req.status != 'pending':
            # Agent already responded — nothing to do
            logger.info(f"Request #{request_id} is {req.status} — timeout skipped.")
            return

        req.status = 'expired'
        req.save(update_fields=['status'])

        notify_agent(req.agent_id, {
            "type": "assignment_expired",
            "request_id": req.id,
            "message": "La demande d'assignation a expiré.",
        })
        notify_patient(req.patient_id, {
            "type": "matching_in_progress",
            "message": "Recherche d'un autre agent disponible…",
        })

        logger.info(f"Request #{request_id} expired — advancing queue #{req.queue_id}.")

        queue = req.queue
        queue.current_index += 1
        queue.save(update_fields=['current_index', 'updated_at'])
        send_to_next_agent.delay(queue.id)

    except AssignmentRequest.DoesNotExist:
        logger.error(f"AssignmentRequest #{request_id} not found.")
    except Exception as e:
        logger.error(
            f"Error in handle_assignment_timeout for request #{request_id}: {e}",
            exc_info=True,
        )


@shared_task(bind=True, name='matching.retry_patient_matching')
def retry_patient_matching(self, patient_profile_id, retry_number):
    """
    Retry matching after all previous candidates failed or were exhausted.
    A fresh candidate list is built so newly approved/available agents are included.
    """
    from matching.models import AssignmentQueue
    from patients.models import PatientProfile

    try:
        patient = PatientProfile.objects.select_related('zone', 'assigned_agent').get(
            id=patient_profile_id
        )

        if patient.assigned_agent_id is not None:
            logger.info(f"Patient {patient_profile_id} already assigned — retry cancelled.")
            return

        agent_ids = _get_candidate_agents(patient)
        if not agent_ids:
            logger.warning(
                f"Patient {patient_profile_id}: still no eligible agents on retry {retry_number}."
            )
            _schedule_retry(patient_profile_id, retry_number)
            return

        queue = AssignmentQueue.objects.create(
            patient=patient,
            ordered_agent_ids=agent_ids,
            current_index=0,
            status='pending',
            retry_count=retry_number,
        )
        send_to_next_agent.delay(queue.id)
        logger.info(
            f"Retry #{retry_number}: queue #{queue.id} created for patient {patient_profile_id}."
        )

    except PatientProfile.DoesNotExist:
        logger.error(f"PatientProfile {patient_profile_id} not found on retry.")
    except Exception as e:
        logger.error(
            f"Error in retry_patient_matching for patient {patient_profile_id}: {e}",
            exc_info=True,
        )
