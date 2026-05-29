import logging
from datetime import date, timedelta

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

            from visits.services import generate_visits_for_subscription
            try:
                generate_visits_for_subscription(sub)
            except Exception:
                logger.exception(
                    "Erreur lors de la génération des visites pour l'abonnement #%s (patient %s).",
                    sub.id,
                    patient.id,
                )

            return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
