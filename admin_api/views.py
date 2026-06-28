from django.db.models import Count, Q, Sum
from django.db import transaction
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from agents.models import AgentProfile, ResidenceZone
from agents.serializers import AgentProfileSerializer, ResidenceZoneSerializer
from agents.zone_approval import (
    apply_pending_zones_to_approved,
    apply_selected_pending_zones,
    clear_pending_zones,
)
from patients.models import PatientProfile, Plan, Subscription
from patients.serializers import PatientProfileSerializer, PlanSerializer
from payments.models import Payment
from payments.serializers import PaymentSerializer
from visits.models import Visit
from visits.serializers import VisitSerializer


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        data = {
            'total_patients': PatientProfile.objects.count(),
            'total_agents': AgentProfile.objects.count(),
            'pending_agents': AgentProfile.objects.filter(approval_status='pending').count(),
            'approved_agents': AgentProfile.objects.filter(approval_status='approved').count(),
            'rejected_agents': AgentProfile.objects.filter(approval_status='rejected').count(),
            'total_visits': Visit.objects.count(),
            'pending_visits': Visit.objects.filter(status='pending').count(),
            'confirmed_visits': Visit.objects.filter(status='confirmed').count(),
            'completed_visits': Visit.objects.filter(status='completed').count(),
            'active_subscriptions': Subscription.objects.filter(status='active').count(),
            'total_revenue': (
                Payment.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
            ),
            'total_plans': Plan.objects.filter(is_active=True).count(),
            'total_zones': ResidenceZone.objects.count(),
            'agents_pending_zone_review': AgentProfile.objects.annotate(
                _pending_cov_count=Count('pending_coverage_zones')
            )
            .filter(Q(pending_residence_zone__isnull=False) | Q(_pending_cov_count__gt=0))
            .count(),
        }
        return Response(data)


class AdminAgentListView(generics.ListAPIView):
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = AgentProfile.objects.select_related(
        'user', 'residence_zone', 'pending_residence_zone'
    ).prefetch_related(
        'schedules',
        'coverage_zones',
        'pending_coverage_zones',
        'documents',
    ).order_by('-created_at')
    filterset_fields = ['approval_status', 'is_available']
    search_fields = ['first_name', 'last_name', 'specialization', 'profession']


class AdminAgentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = AgentProfile.objects.select_related(
        'user', 'residence_zone', 'pending_residence_zone'
    ).prefetch_related(
        'schedules',
        'coverage_zones',
        'pending_coverage_zones',
        'documents',
    )


class AdminApproveAgentView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            agent = AgentProfile.objects.select_related('pending_residence_zone').prefetch_related(
                'pending_coverage_zones'
            ).get(pk=pk)
            with transaction.atomic():
                agent.approval_status = 'approved'
                agent.save(update_fields=['approval_status', 'updated_at'])
                apply_pending_zones_to_approved(agent)
            return Response({'message': f"Agent '{agent.display_name}' approuvé avec succès."})
        except AgentProfile.DoesNotExist:
            return Response({'error': 'Agent introuvable.'}, status=status.HTTP_404_NOT_FOUND)


class AdminRejectAgentView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            agent = AgentProfile.objects.get(pk=pk)
            with transaction.atomic():
                agent.approval_status = 'rejected'
                agent.save(update_fields=['approval_status', 'updated_at'])
                clear_pending_zones(agent)
            return Response({'message': f"Agent '{agent.display_name}' rejeté."})
        except AgentProfile.DoesNotExist:
            return Response({'error': 'Agent introuvable.'}, status=status.HTTP_404_NOT_FOUND)


class AdminApproveAgentZonesView(APIView):
    """Valide les zones demandées par un agent déjà approuvé (copie pending → opérationnel)."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            agent = AgentProfile.objects.select_related('pending_residence_zone').prefetch_related(
                'pending_coverage_zones'
            ).get(pk=pk)
        except AgentProfile.DoesNotExist:
            return Response({'error': 'Agent introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if agent.approval_status != 'approved':
            return Response(
                {'error': "Seuls les agents déjà approuvés peuvent recevoir une validation de zones."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        has_pending = agent.pending_residence_zone_id is not None or agent.pending_coverage_zones.exists()
        if not has_pending:
            return Response(
                {'error': 'Aucune demande de zones en attente pour cet agent.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        apply_pending_zones_to_approved(agent)
        return Response(
            {'message': f"Zones de « {agent.display_name} » validées et appliquées."},
            status=status.HTTP_200_OK,
        )


class AdminRejectAgentZonesView(APIView):
    """Refuse la demande de zones : efface les champs en attente sans modifier les zones actives."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            agent = AgentProfile.objects.get(pk=pk)
        except AgentProfile.DoesNotExist:
            return Response({'error': 'Agent introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        has_pending = agent.pending_residence_zone_id is not None or agent.pending_coverage_zones.exists()
        if not has_pending:
            return Response(
                {'error': 'Aucune demande de zones en attente pour cet agent.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        clear_pending_zones(agent)
        return Response(
            {'message': f"Demande de zones refusée pour « {agent.display_name} »."},
            status=status.HTTP_200_OK,
        )


class AdminReviewAgentZonesInputSerializer(serializers.Serializer):
    approve_residence = serializers.BooleanField(required=False, default=True)
    approved_coverage_zone_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )


class AdminReviewAgentZonesView(APIView):
    """Valide partiellement une demande de zones (sélection admin)."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            agent = AgentProfile.objects.select_related('pending_residence_zone').prefetch_related(
                'pending_coverage_zones'
            ).get(pk=pk)
        except AgentProfile.DoesNotExist:
            return Response({'error': 'Agent introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if agent.approval_status != 'approved':
            return Response(
                {'error': "Seuls les agents déjà approuvés peuvent recevoir une validation de zones."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_pending = agent.pending_residence_zone_id is not None or agent.pending_coverage_zones.exists()
        if not has_pending:
            return Response(
                {'error': 'Aucune demande de zones en attente pour cet agent.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminReviewAgentZonesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approve_residence = serializer.validated_data.get('approve_residence', True)
        approved_cov_ids = serializer.validated_data.get('approved_coverage_zone_ids', [])
        pending_cov_ids = set(agent.pending_coverage_zones.values_list('pk', flat=True))
        invalid_ids = [zid for zid in approved_cov_ids if zid not in pending_cov_ids]
        if invalid_ids:
            return Response(
                {'error': 'Certaines zones sélectionnées ne font pas partie de la demande en attente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        apply_selected_pending_zones(
            profile=agent,
            approve_residence=approve_residence,
            approved_coverage_zone_ids=approved_cov_ids,
        )
        return Response(
            {'message': f"Sélection des zones appliquée pour « {agent.display_name} »."},
            status=status.HTTP_200_OK,
        )


class AdminPatientListView(generics.ListAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = PatientProfile.objects.select_related('user', 'zone').order_by('-created_at')
    search_fields = ['first_name', 'last_name', 'city']
    filterset_fields = ['gender', 'city']


class AdminPatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = PatientProfile.objects.select_related('user', 'zone')


class AdminVisitListView(generics.ListAPIView):
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Visit.objects.select_related('patient', 'agent', 'vital_signs', 'pre_screening').order_by(
        '-created_at'
    )
    filterset_fields = ['status']
    search_fields = ['patient__first_name', 'patient__last_name', 'agent__first_name', 'agent__last_name']


class AdminVisitDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Visit.objects.select_related('patient', 'agent', 'vital_signs', 'pre_screening', 'review')


class AdminPlanListCreateView(generics.ListCreateAPIView):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Plan.objects.all()


class AdminPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Plan.objects.all()


class AdminZoneListCreateView(generics.ListCreateAPIView):
    serializer_class = ResidenceZoneSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ResidenceZone.objects.all()


class AdminZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResidenceZoneSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ResidenceZone.objects.all()


class AdminPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Payment.objects.select_related('subscription__patient', 'subscription__plan').order_by('-created_at')
    filterset_fields = ['status', 'payment_method']


class AdminPaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Payment.objects.select_related('subscription__patient', 'subscription__plan')


# ─── Admin Settings ───────────────────────────────────────────────────────────

class AdminSettingSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    value = serializers.CharField()
    description = serializers.CharField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AdminSettingListView(APIView):
    """GET /api/admin/settings/ — list all application settings."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from admin_api.models import AdminSetting
        settings_qs = AdminSetting.objects.all()
        data = AdminSettingSerializer(settings_qs, many=True).data
        return Response(data)


class AdminSettingUpdateView(APIView):
    """PATCH /api/admin/settings/<key>/ — update a single setting value."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, key):
        from admin_api.models import AdminSetting
        try:
            setting = AdminSetting.objects.get(key=key)
        except AdminSetting.DoesNotExist:
            return Response({'detail': f"Paramètre '{key}' introuvable."}, status=status.HTTP_404_NOT_FOUND)

        new_value = request.data.get('value')
        if new_value is None:
            return Response({'detail': "Le champ 'value' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        setting.value = new_value
        setting.save(update_fields=['value', 'updated_at'])
        return Response(AdminSettingSerializer(setting).data)
