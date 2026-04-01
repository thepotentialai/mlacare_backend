from datetime import date, timedelta
import logging

from kombu.exceptions import OperationalError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsPatient

from .models import Plan, Subscription
from .serializers import PatientProfileSerializer, PlanSerializer, SubscriptionSerializer

logger = logging.getLogger(__name__)


class PatientProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated, IsPatient]

    def get_object(self):
        return self.request.user.patient_profile


class PlanListView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    queryset = Plan.objects.filter(is_active=True)


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        sub = request.user.patient_profile.subscriptions.filter(status='active').first()
        if sub:
            return Response(SubscriptionSerializer(sub).data)
        return Response({'detail': 'Aucun abonnement actif.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = SubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            patient = request.user.patient_profile
            patient.subscriptions.filter(status='active').update(status='cancelled')
            plan = serializer.validated_data['plan']
            today = date.today()
            sub = Subscription.objects.create(
                patient=patient,
                plan=plan,
                start_date=today,
                end_date=today + timedelta(days=30),
                status='active',
            )

            # ── Trigger patient-agent matching ──────────────────────────────
            # Only start matching if patient has no assigned agent yet
            if patient.assigned_agent_id is None:
                from matching.tasks import start_patient_matching
                try:
                    start_patient_matching.delay(patient.id)
                except OperationalError:
                    # Keep subscription creation successful if broker is temporarily unavailable.
                    logger.exception(
                        "Celery broker unreachable while starting patient matching for patient %s",
                        patient.id,
                    )
                except Exception:
                    logger.exception(
                        "Unexpected error while starting patient matching for patient %s",
                        patient.id,
                    )

                # In-app notice: assignment can take up to <setting> to complete
                from admin_api.models import AdminSetting
                from notifications.models import Notification
                try:
                    duration = AdminSetting.objects.get(key='assignment_notice_duration').value
                except AdminSetting.DoesNotExist:
                    duration = "24 heures"
                Notification.objects.create(
                    user=request.user,
                    title="Assignation d'un agent en cours",
                    message=(
                        f"Votre demande d'assignation est en cours de traitement. "
                        f"Cela prend généralement {duration}."
                    ),
                    type='system',
                )
            # ───────────────────────────────────────────────────────────────

            return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
