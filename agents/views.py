from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAgent, IsApprovedAgent, IsApprovedOrRevisionAgent, IsRevisionRequiredAgent

from .approval import resubmit_agent_application
from .models import AgentDocument, AgentProfile, AgentSchedule, ResidenceZone
from .serializers import (
    AgentDocumentSerializer,
    AgentProfileSerializer,
    AgentScheduleSerializer,
    ResidenceZoneSerializer,
)


class AgentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AgentProfileSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsApprovedOrRevisionAgent()]
        return [IsAuthenticated(), IsAgent()]

    def get_object(self):
        return get_object_or_404(
            AgentProfile.objects.select_related(
                'user', 'residence_zone', 'pending_residence_zone', 'rejected_by'
            ).prefetch_related(
                'schedules',
                'coverage_zones',
                'pending_coverage_zones',
                'documents',
            ),
            user=self.request.user,
        )


class AgentAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedAgent]

    def patch(self, request):
        profile = request.user.agent_profile
        profile.is_available = not profile.is_available
        profile.save()
        return Response({'is_available': profile.is_available})


class AgentDocumentView(generics.CreateAPIView):
    serializer_class = AgentDocumentSerializer
    permission_classes = [IsAuthenticated, IsApprovedOrRevisionAgent]

    def perform_create(self, serializer):
        profile = self.request.user.agent_profile
        document_type = serializer.validated_data['document_type']
        if document_type != 'other':
            AgentDocument.objects.filter(
                agent=profile,
                document_type=document_type,
            ).delete()
        serializer.save(agent=profile)


class AgentDocumentDetailView(generics.DestroyAPIView):
    serializer_class = AgentDocumentSerializer
    permission_classes = [IsAuthenticated, IsApprovedOrRevisionAgent]

    def get_queryset(self):
        return AgentDocument.objects.filter(agent=self.request.user.agent_profile)


class AgentResubmitView(APIView):
    permission_classes = [IsAuthenticated, IsRevisionRequiredAgent]

    def post(self, request):
        profile = request.user.agent_profile
        try:
            resubmit_agent_application(profile)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'message': (
                    'Votre candidature a été resoumise. '
                    'Notre équipe va la réexaminer.'
                ),
            },
            status=status.HTTP_200_OK,
        )


class ResidenceZoneListView(generics.ListAPIView):
    serializer_class = ResidenceZoneSerializer
    permission_classes = [AllowAny]
    queryset = ResidenceZone.objects.all()


class AgentScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = AgentScheduleSerializer
    permission_classes = [IsAuthenticated, IsApprovedOrRevisionAgent]

    def get_queryset(self):
        return AgentSchedule.objects.filter(agent=self.request.user.agent_profile).order_by('day_of_week')

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user.agent_profile)


class AgentScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentScheduleSerializer
    permission_classes = [IsAuthenticated, IsApprovedOrRevisionAgent]

    def get_queryset(self):
        return AgentSchedule.objects.filter(agent=self.request.user.agent_profile)
