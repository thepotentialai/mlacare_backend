import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAgent
from accounts.permissions import IsAdmin
from matching.models import AssignmentQueue, AssignmentRequest
from matching.serializers import AssignmentQueueSerializer, AssignmentRequestSerializer
from matching.tasks import notify_agent, notify_patient, send_to_next_agent

logger = logging.getLogger(__name__)


def _revoke_timeout_task(celery_task_id):
    """Revoke a scheduled Celery timeout task (best-effort)."""
    if not celery_task_id:
        return
    try:
        from mlacare.celery import app as celery_app
        celery_app.control.revoke(celery_task_id, terminate=False)
    except Exception as e:
        logger.warning(f"Could not revoke Celery task {celery_task_id}: {e}")


class PendingAssignmentRequestListView(APIView):
    """GET  /api/matching/requests/pending/ — agent's pending assignment requests."""

    permission_classes = [IsAuthenticated, IsAgent]

    def get(self, request):
        agent = request.user.agent_profile
        requests_qs = (
            AssignmentRequest.objects
            .filter(agent=agent, status='pending')
            .select_related('patient__zone', 'queue')
            .order_by('created_at')
        )
        return Response(AssignmentRequestSerializer(requests_qs, many=True).data)


class AcceptAssignmentRequestView(APIView):
    """POST /api/matching/requests/<pk>/accept/ — agent accepts a patient assignment."""

    permission_classes = [IsAuthenticated, IsAgent]

    def post(self, request, pk):
        agent = request.user.agent_profile
        try:
            req = (
                AssignmentRequest.objects
                .select_related('patient', 'agent', 'queue')
                .get(pk=pk, agent=agent, status='pending')
            )
        except AssignmentRequest.DoesNotExist:
            return Response(
                {'detail': 'Demande introuvable ou déjà traitée.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        _revoke_timeout_task(req.celery_task_id)

        req.status = 'accepted'
        req.responded_at = timezone.now()
        req.save(update_fields=['status', 'responded_at'])

        queue = req.queue
        queue.status = 'assigned'
        queue.save(update_fields=['status', 'updated_at'])

        # Assign agent to patient profile
        patient = req.patient
        patient.assigned_agent = agent
        patient.save(update_fields=['assigned_agent'])

        # Generate visits for the patient's active subscription now that an agent is assigned
        subscription = patient.subscriptions.filter(status='active').first()
        if subscription:
            from visits.services import generate_visits_for_subscription
            try:
                generate_visits_for_subscription(subscription)
            except Exception:
                logger.exception(
                    "Erreur lors de la génération des visites pour l'abonnement #%s (patient %s).",
                    subscription.id,
                    patient.id,
                )

        # Cancel every other pending request in this queue and notify those agents
        other_pending = AssignmentRequest.objects.filter(
            queue=queue, status='pending'
        ).exclude(pk=req.pk).select_related('agent')
        for other in other_pending:
            other.status = 'cancelled'
            other.save(update_fields=['status'])
            _revoke_timeout_task(other.celery_task_id)
            notify_agent(other.agent_id, {
                "type": "assignment_cancelled",
                "request_id": other.id,
                "message": "La demande d'assignation a été annulée (patient déjà assigné).",
            })

        notify_patient(patient.id, {
            "type": "assignment_accepted",
            "request_id": req.id,
            "agent_id": agent.id,
            "agent_name": agent.full_name,
            "agent_profession": agent.get_profession_display(),
            "message": f"L'agent {agent.full_name} a accepté de vous prendre en charge.",
        })

        # Persist in-app notification for patient
        from notifications.models import Notification
        Notification.objects.create(
            user=patient.user,
            title="Agent assigné",
            message=(
                f"L'agent {agent.full_name} ({agent.get_profession_display()}) "
                "a accepté de vous prendre en charge."
            ),
            type='system',
        )

        logger.info(f"Agent {agent.id} accepted request #{req.id} — patient {patient.id} assigned.")
        return Response({'detail': 'Demande acceptée. Patient assigné avec succès.'})


class DeclineAssignmentRequestView(APIView):
    """POST /api/matching/requests/<pk>/decline/ — agent declines a patient assignment."""

    permission_classes = [IsAuthenticated, IsAgent]

    def post(self, request, pk):
        agent = request.user.agent_profile
        try:
            req = (
                AssignmentRequest.objects
                .select_related('patient', 'agent', 'queue')
                .get(pk=pk, agent=agent, status='pending')
            )
        except AssignmentRequest.DoesNotExist:
            return Response(
                {'detail': 'Demande introuvable ou déjà traitée.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        _revoke_timeout_task(req.celery_task_id)

        req.status = 'declined'
        req.responded_at = timezone.now()
        req.save(update_fields=['status', 'responded_at'])

        notify_patient(req.patient_id, {
            "type": "matching_in_progress",
            "message": "Recherche d'un autre agent disponible…",
        })

        queue = req.queue
        queue.current_index += 1
        queue.save(update_fields=['current_index', 'updated_at'])

        send_to_next_agent.delay(queue.id)

        logger.info(f"Agent {agent.id} declined request #{req.id} — advancing queue #{queue.id}.")
        return Response({'detail': 'Demande refusée. Passage au prochain agent.'})


class AdminAssignmentQueueListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        queues = (
            AssignmentQueue.objects
            .select_related('patient__zone')
            .prefetch_related('requests__agent')
            .order_by('-created_at')
        )
        return Response(AssignmentQueueSerializer(queues, many=True).data)


class AdminAssignmentRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        requests_qs = (
            AssignmentRequest.objects
            .select_related('patient__zone', 'agent', 'queue')
            .order_by('-created_at')
        )
        return Response(AssignmentRequestSerializer(requests_qs, many=True).data)
