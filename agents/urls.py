from django.urls import path

from . import views

urlpatterns = [
    path('profile/', views.AgentProfileView.as_view(), name='agent-profile'),
    path('availability/', views.AgentAvailabilityView.as_view(), name='agent-availability'),
    path('resubmit/', views.AgentResubmitView.as_view(), name='agent-resubmit'),
    path('documents/', views.AgentDocumentView.as_view(), name='agent-documents'),
    path('documents/<int:pk>/', views.AgentDocumentDetailView.as_view(), name='agent-document-detail'),
    path('schedules/', views.AgentScheduleListCreateView.as_view(), name='agent-schedule-list'),
    path('schedules/<int:pk>/', views.AgentScheduleDetailView.as_view(), name='agent-schedule-detail'),
    # Public list for dropdowns (patients + agents)
    path('residence-zones/', views.ResidenceZoneListView.as_view(), name='residence-zone-list'),
    # Backward-compatible alias (old endpoint name)
    path('all-zones/', views.ResidenceZoneListView.as_view(), name='zone-list'),
]
