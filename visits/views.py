import math
from datetime import datetime

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAgent, IsPatient

from .models import HealthReport, ReportAttachment, Visit, VitalSigns, VisitReview
from .serializers import HealthReportSerializer, VisitReviewSerializer, VisitSerializer, VitalSignsSerializer


class VisitListCreateView(generics.ListCreateAPIView):
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Visit.objects.filter(patient=user.patient_profile).select_related('agent', 'vital_signs', 'review')
        if user.role == 'agent':
            return Visit.objects.filter(agent=user.agent_profile).select_related('patient', 'vital_signs', 'review')
        return Visit.objects.select_related('patient', 'agent', 'vital_signs', 'review').all()

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

    def create(self, request, *args, **kwargs):
        if request.user.role != 'patient':
            return Response({'error': 'Seuls les patients peuvent créer une visite.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


AGENT_TRANSITIONS = {
    'pending': {'confirmed'},
    'confirmed': {'in_progress'},
    'in_progress': {'completed', 'absent'},
    'absent': {'rescheduled'},
    'rescheduled': {'pending'},
}

PATIENT_ADMIN_TRANSITIONS = {
    'pending': {'cancelled'},
    'confirmed': {'cancelled'},
}

REQUIRED_VITAL_FIELDS = {
    'blood_pressure_sys': 'pression artérielle systolique',
    'blood_pressure_dia': 'pression artérielle diastolique',
    'heart_rate': 'fréquence cardiaque',
    'temperature': 'température',
    'respiratory_rate': 'fréquence respiratoire',
    'spo2': 'saturation en oxygène (SpO2)',
    'blood_glucose': 'glycémie',
    'weight': 'poids',
    'height': 'taille',
}


class VisitDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Visit.objects.filter(patient=user.patient_profile).select_related('review')
        if user.role == 'agent':
            return Visit.objects.filter(agent=user.agent_profile).select_related('review')
        return Visit.objects.select_related('review').all()

    def partial_update(self, request, *args, **kwargs):
        visit = self.get_object()
        new_status = request.data.get('status')

        if new_status and new_status != visit.status:
            user = request.user
            if user.role == 'agent':
                allowed = AGENT_TRANSITIONS.get(visit.status, set())
            else:
                allowed = PATIENT_ADMIN_TRANSITIONS.get(visit.status, set())

            if new_status not in allowed:
                return Response(
                    {
                        'error': (
                            f"Transition '{visit.status}' → '{new_status}' non autorisée "
                            f"pour le rôle '{user.role}'."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Block starting a visit if a previous one in the same cycle is not yet done.
            # Confirming is always allowed; only in_progress is gated.
            if new_status == 'in_progress' and visit.subscription_id and visit.visit_number:
                blocking = Visit.objects.filter(
                    subscription_id=visit.subscription_id,
                    visit_number__lt=visit.visit_number,
                    status__in=['pending', 'confirmed', 'in_progress'],
                ).exists()
                if blocking:
                    return Response(
                        {
                            'error': (
                                "Impossible de démarrer cette visite : la visite précédente "
                                "du cycle n'est pas encore terminée."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if new_status == 'rescheduled':
                reschedule_date = request.data.get('reschedule_date')
                reschedule_time = request.data.get('reschedule_time')

                if not reschedule_date or not reschedule_time:
                    return Response(
                        {
                            'error': (
                                "Veuillez fournir une nouvelle date (reschedule_date) "
                                "et une nouvelle heure (reschedule_time) pour reporter la visite."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                try:
                    new_date = datetime.strptime(reschedule_date, '%Y-%m-%d').date()
                    new_time = datetime.strptime(reschedule_time, '%H:%M').time()
                except ValueError:
                    return Response(
                        {
                            'error': (
                                "Format de date ou d'heure invalide. "
                                "Utilisez YYYY-MM-DD pour la date et HH:MM pour l'heure."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if new_date < timezone.now().date():
                    return Response(
                        {'error': "La date de reprogrammation ne peut pas être dans le passé."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Save original date before rescheduling
                original_dt = datetime.combine(visit.scheduled_date, visit.scheduled_time)
                visit.rescheduled_from = timezone.make_aware(original_dt)
                visit.scheduled_date = new_date
                visit.scheduled_time = new_time
                visit.status = 'pending'
                visit.save(update_fields=['rescheduled_from', 'scheduled_date', 'scheduled_time', 'status'])
                return Response(VisitSerializer(visit).data)

            if new_status == 'completed':
                try:
                    vitals = visit.vital_signs
                except VitalSigns.DoesNotExist:
                    return Response(
                        {
                            'error': (
                                "Impossible de terminer la visite : veuillez renseigner "
                                "les informations vitales avant la clôture."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                missing = [
                    label for field, label in REQUIRED_VITAL_FIELDS.items()
                    if getattr(vitals, field) is None
                ]
                if missing:
                    return Response(
                        {
                            'error': (
                                "Impossible de terminer la visite : informations vitales "
                                f"manquantes ({', '.join(missing)})."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)

        # Auto-set completed_at when visit is marked completed
        if new_status == 'completed' and response.status_code == 200:
            visit.refresh_from_db()
            if not visit.completed_at:
                visit.completed_at = timezone.now()
                visit.save(update_fields=['completed_at'])

        return response


class VitalSignsView(APIView):
    permission_classes = [IsAuthenticated, IsAgent]

    def get(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id, agent=request.user.agent_profile)
            vitals = visit.vital_signs
            return Response(VitalSignsSerializer(vitals).data)
        except Visit.DoesNotExist:
            return Response({'error': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        except VitalSigns.DoesNotExist:
            return Response({'error': 'Aucun signe vital enregistré pour cette visite.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id, agent=request.user.agent_profile)
        except Visit.DoesNotExist:
            return Response({'error': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = VitalSignsSerializer(data=request.data)
        if serializer.is_valid():
            VitalSigns.objects.update_or_create(
                visit=visit,
                defaults=serializer.validated_data,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthReportListCreateView(generics.ListCreateAPIView):
    serializer_class = HealthReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return HealthReport.objects.filter(patient=user.patient_profile).prefetch_related('attachments')
        return HealthReport.objects.prefetch_related('attachments').all()

    def perform_create(self, serializer):
        report = serializer.save(patient=self.request.user.patient_profile)
        for file_obj in self.request.FILES.getlist('attachments'):
            ReportAttachment.objects.create(report=report, file=file_obj)


class HealthReportDetailView(generics.RetrieveAPIView):
    serializer_class = HealthReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return HealthReport.objects.filter(patient=user.patient_profile)
        return HealthReport.objects.all()


class ReportAttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, attachment_id):
        try:
            attachment = ReportAttachment.objects.select_related('report__patient__user').get(id=attachment_id)
        except ReportAttachment.DoesNotExist:
            return Response({'error': 'Pièce jointe introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'patient' and attachment.report.patient.user_id != request.user.id:
            return Response({'error': 'Action non autorisée.'}, status=status.HTTP_403_FORBIDDEN)

        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitReviewView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id, patient=request.user.patient_profile)
        except Visit.DoesNotExist:
            return Response({'error': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            review = visit.review
            return Response(VisitReviewSerializer(review).data)
        except VisitReview.DoesNotExist:
            return Response(None, status=status.HTTP_200_OK)

    def post(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id, patient=request.user.patient_profile)
        except Visit.DoesNotExist:
            return Response({'error': 'Visite introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if visit.status != 'completed':
            return Response(
                {'error': "Vous ne pouvez noter qu'une visite terminée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if VisitReview.objects.filter(visit=visit).exists():
            return Response(
                {'error': "Un avis a déjà été soumis pour cette visite."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VisitReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(visit=visit)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlanProgressView(APIView):
    """
    GET /api/visits/plan-progress/

    Retourne la progression des visites par rapport au plan d'abonnement actif.
    - patient : progression de son propre abonnement.
    - agent   : progression globale de ses patients assignés.
    - admin   : progression globale de tous les patients.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        if user.role == 'patient':
            sub = user.patient_profile.subscriptions.filter(status='active').first()
            if not sub:
                return Response({'detail': 'Aucun abonnement actif.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(self._progress_for_subscription(sub, today))

        if user.role == 'agent':
            visits_qs = Visit.objects.filter(
                agent=user.agent_profile,
                subscription__isnull=False,
            )
            return Response(self._aggregate_progress(visits_qs, today))

        # admin
        visits_qs = Visit.objects.filter(subscription__isnull=False)
        return Response(self._aggregate_progress(visits_qs, today))

    @staticmethod
    def _progress_for_subscription(sub, today):
        visits_qs = sub.visits.all()
        visits_expected = visits_qs.count()
        visits_completed = visits_qs.filter(status='completed').count()
        visits_absent = visits_qs.filter(status='absent').count()
        visits_cancelled = visits_qs.filter(status='cancelled').count()
        visits_missed = visits_qs.filter(
            status__in=['pending', 'confirmed'],
            scheduled_date__lt=today,
        ).count()
        visits_pending = visits_qs.filter(
            status__in=['pending', 'confirmed', 'in_progress'],
            scheduled_date__gte=today,
        ).count()
        rate = math.floor((visits_completed / visits_expected) * 100) if visits_expected else 0
        return {
            'visits_expected': visits_expected,
            'visits_completed': visits_completed,
            'visits_pending': visits_pending,
            'visits_missed': visits_missed,
            'visits_absent': visits_absent,
            'visits_cancelled': visits_cancelled,
            'completion_rate': rate,
            'plan_name': sub.plan.name,
            'subscription_start': sub.start_date,
            'subscription_end': sub.end_date,
        }

    @staticmethod
    def _aggregate_progress(visits_qs, today):
        visits_expected = visits_qs.count()
        visits_completed = visits_qs.filter(status='completed').count()
        visits_absent = visits_qs.filter(status='absent').count()
        visits_cancelled = visits_qs.filter(status='cancelled').count()
        visits_missed = visits_qs.filter(
            status__in=['pending', 'confirmed'],
            scheduled_date__lt=today,
        ).count()
        visits_pending = visits_qs.filter(
            status__in=['pending', 'confirmed', 'in_progress'],
            scheduled_date__gte=today,
        ).count()
        rate = math.floor((visits_completed / visits_expected) * 100) if visits_expected else 0
        return {
            'visits_expected': visits_expected,
            'visits_completed': visits_completed,
            'visits_pending': visits_pending,
            'visits_missed': visits_missed,
            'visits_absent': visits_absent,
            'visits_cancelled': visits_cancelled,
            'completion_rate': rate,
        }
