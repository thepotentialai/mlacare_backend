from django.urls import path

from . import views

urlpatterns = [
    path('', views.VisitListCreateView.as_view(), name='visit-list'),
    path('plan-progress/', views.PlanProgressView.as_view(), name='visit-plan-progress'),
    path('<int:pk>/', views.VisitDetailView.as_view(), name='visit-detail'),
    path('<int:visit_id>/vitals/', views.VitalSignsView.as_view(), name='visit-vitals'),
    path('<int:visit_id>/review/', views.VisitReviewView.as_view(), name='visit-review'),
    path('health-reports/', views.HealthReportListCreateView.as_view(), name='health-report-list'),
    path('health-reports/<int:pk>/', views.HealthReportDetailView.as_view(), name='health-report-detail'),
    path('health-reports/attachments/<int:attachment_id>/', views.ReportAttachmentDeleteView.as_view(), name='health-report-attachment-delete'),
]
