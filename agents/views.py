from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAgent

from .models import AgentDocument, AgentProfile, AgentSchedule, ResidenceZone
from .serializers import (
    AgentDocumentSerializer,
    AgentProfileSerializer,
    AgentScheduleSerializer,
    ResidenceZoneSerializer,
)


class AgentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_object(self):
        return get_object_or_404(
            AgentProfile.objects.select_related(
                'user', 'residence_zone', 'pending_residence_zone'
            ).prefetch_related(
                'schedules',
                'coverage_zones',
                'pending_coverage_zones',
                'documents',
            ),
            user=self.request.user,
        )


class AgentAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsAgent]

    def patch(self, request):
        profile = request.user.agent_profile
        profile.is_available = not profile.is_available
        profile.save()
        return Response({'is_available': profile.is_available})


class AgentDocumentView(generics.CreateAPIView):
    serializer_class = AgentDocumentSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user.agent_profile)


class ResidenceZoneListView(generics.ListAPIView):
    serializer_class = ResidenceZoneSerializer
    permission_classes = [AllowAny]
    queryset = ResidenceZone.objects.all()


class AgentScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = AgentScheduleSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        return AgentSchedule.objects.filter(agent=self.request.user.agent_profile).order_by('day_of_week')

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user.agent_profile)


class AgentScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentScheduleSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        return AgentSchedule.objects.filter(agent=self.request.user.agent_profile)
