from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Payment
from .serializers import PaymentSerializer


class PaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return Payment.objects.select_related('subscription__patient', 'subscription__plan').all()
        if user.role == 'patient':
            return Payment.objects.filter(
                subscription__patient=user.patient_profile
            ).select_related('subscription__plan')
        return Payment.objects.none()

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('patient', 'admin'):
            return Response({'error': 'Action non autorisée.'}, status=status.HTTP_403_FORBIDDEN)
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            payment = Payment.objects.get(id=response.data['id'])
            # Current system has no gateway callback; we mark as success at creation.
            payment.status = 'success'
            payment.save(update_fields=['status'])
            response.data['status'] = 'success'
            response.data['status_label'] = payment.get_status_display()
        return response
