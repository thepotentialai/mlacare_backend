from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('agents/', views.AdminAgentListView.as_view(), name='admin-agent-list'),
    path('agents/<int:pk>/', views.AdminAgentDetailView.as_view(), name='admin-agent-detail'),
    path('agents/<int:pk>/approve/', views.AdminApproveAgentView.as_view(), name='admin-agent-approve'),
    path('agents/<int:pk>/reject/', views.AdminRejectAgentView.as_view(), name='admin-agent-reject'),
    path('patients/', views.AdminPatientListView.as_view(), name='admin-patient-list'),
    path('patients/<int:pk>/', views.AdminPatientDetailView.as_view(), name='admin-patient-detail'),
    path('visits/', views.AdminVisitListView.as_view(), name='admin-visit-list'),
    path('visits/<int:pk>/', views.AdminVisitDetailView.as_view(), name='admin-visit-detail'),
    path('plans/', views.AdminPlanListCreateView.as_view(), name='admin-plan-list'),
    path('plans/<int:pk>/', views.AdminPlanDetailView.as_view(), name='admin-plan-detail'),
    path('zones/', views.AdminZoneListCreateView.as_view(), name='admin-zone-list'),
    path('zones/<int:pk>/', views.AdminZoneDetailView.as_view(), name='admin-zone-detail'),
    path('payments/', views.AdminPaymentListView.as_view(), name='admin-payment-list'),
    path('payments/<int:pk>/', views.AdminPaymentDetailView.as_view(), name='admin-payment-detail'),
    # Application settings
    path('settings/', views.AdminSettingListView.as_view(), name='admin-setting-list'),
    path('settings/<str:key>/', views.AdminSettingUpdateView.as_view(), name='admin-setting-update'),
]
