from django.urls import path

from . import views

urlpatterns = [
    path('profile/', views.PatientProfileView.as_view(), name='patient-profile'),
    path('subscription/', views.SubscriptionView.as_view(), name='patient-subscription'),
    path('plans/', views.PlanListView.as_view(), name='plan-list'),
]
