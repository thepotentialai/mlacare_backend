from django.urls import path

from . import views

urlpatterns = [
    path('requests/pending/', views.PendingAssignmentRequestListView.as_view(), name='assignment-requests-pending'),
    path('requests/<int:pk>/accept/', views.AcceptAssignmentRequestView.as_view(), name='assignment-request-accept'),
    path('requests/<int:pk>/decline/', views.DeclineAssignmentRequestView.as_view(), name='assignment-request-decline'),
    path('admin/queues/', views.AdminAssignmentQueueListView.as_view(), name='admin-assignment-queue-list'),
    path('admin/requests/', views.AdminAssignmentRequestListView.as_view(), name='admin-assignment-request-list'),
]
