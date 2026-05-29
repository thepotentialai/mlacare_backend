from django.urls import path

from . import views

urlpatterns = [
    path('', views.PaymentListCreateView.as_view(), name='payment-list'),
    path('donations/init/', views.DonationInitView.as_view(), name='donation-init'),
    path('donations/payment_status/', views.DonationPaymentStatusView.as_view(), name='donation-payment-status'),
]
