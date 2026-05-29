from django.conf import settings
from django.db import transaction as db_transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import DonationTransaction, PaygateDonationStatus, Payment
from .serializers import (
    DonationInitSerializer,
    DonationTransactionSerializer,
    PaymentSerializer,
    PaygateCallbackSerializer,
)
from .services.paygate import initiate_paygate_payment, verify_paygate_status


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


class DonationInitThrottle(AnonRateThrottle):
    rate = '20/hour'


class DonationInitView(generics.GenericAPIView):
    serializer_class = DonationInitSerializer
    permission_classes = [AllowAny]
    throttle_classes = [DonationInitThrottle]

    def post(self, request, *args, **kwargs):
        if not settings.PAYGATE_KEY:
            return Response(
                {'error': 'Configuration PayGate manquante sur le serveur.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data['donation_frequency'] == 'monthly':
            return Response(
                {'error': 'Le paiement mensuel n’est pas encore disponible.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donation = DonationTransaction.objects.create(
            donor_name=data.get('donor_name') or '',
            donor_email=data.get('donor_email') or '',
            amount=data['amount'],
            phone_number=data['phone_number'],
            payment_method=data['payment_method'],
            status='pending',
        )
        donation.identifier = str(donation.id)
        donation.save(update_fields=['identifier', 'updated_at'])

        try:
            paygate_response = initiate_paygate_payment(
                phone_number=donation.phone_number,
                amount=str(donation.amount),
                identifier=donation.identifier,
                network=donation.payment_method,
            )
        except Exception as exc:
            donation.status = 'failed'
            donation.save(update_fields=['status', 'updated_at'])
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        tx_reference = paygate_response.get('tx_reference')
        if not tx_reference:
            donation.status = 'failed'
            donation.save(update_fields=['status', 'updated_at'])
            return Response(
                {'error': "Erreur PayGate lors de l'initialisation", 'paygate_response': paygate_response},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PaygateDonationStatus.objects.update_or_create(
            donation=donation,
            defaults={
                'tx_reference': tx_reference,
                'identifier': donation.identifier,
                'payment_reference': '',
                'amount': donation.amount,
                'payment_method': donation.payment_method,
                'phone_number': donation.phone_number,
            },
        )
        donation.tx_reference = tx_reference
        donation.status = 'pending'
        donation.save(update_fields=['tx_reference', 'status', 'updated_at'])

        return Response(
            {
                'donation': DonationTransactionSerializer(donation).data,
                'paygate_response': paygate_response,
            },
            status=status.HTTP_200_OK,
        )


class DonationPaymentStatusView(generics.GenericAPIView):
    serializer_class = PaygateCallbackSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if request.data:
            received_data = dict(request.data)
        elif request.POST:
            received_data = dict(request.POST)
            for key, value in received_data.items():
                if isinstance(value, list):
                    received_data[key] = value[0] if len(value) == 1 else None
        else:
            received_data = {}

        callback_serializer = self.get_serializer(data=received_data)
        callback_serializer.is_valid(raise_exception=True)
        data = callback_serializer.validated_data

        donation = DonationTransaction.objects.filter(identifier=data['identifier']).first()
        if not donation:
            return Response({'error': 'Transaction introuvable'}, status=status.HTTP_404_NOT_FOUND)

        if donation.status == 'completed':
            return Response({'detail': 'Paiement deja traite'}, status=status.HTTP_200_OK)

        donation.tx_reference = data['tx_reference']
        try:
            status_data = verify_paygate_status(data['tx_reference'])
        except Exception as exc:
            donation.status = 'failed'
            donation.save(update_fields=['tx_reference', 'status', 'updated_at'])
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if status_data.get('status') == 0:
            new_status = 'completed'
        else:
            new_status = 'failed'

        with db_transaction.atomic():
            donation.status = new_status
            donation.save(update_fields=['tx_reference', 'status', 'updated_at'])
            PaygateDonationStatus.objects.update_or_create(
                donation=donation,
                defaults={
                    'tx_reference': data['tx_reference'],
                    'identifier': data['identifier'],
                    'payment_reference': data.get('payment_reference') or '',
                    'amount': data.get('amount'),
                    'datetime': data.get('datetime'),
                    'payment_method': data.get('payment_method') or '',
                    'phone_number': data.get('phone_number') or '',
                },
            )

        if new_status == 'failed':
            return Response(
                {'detail': 'Paiement echoue', 'paygate_status': status_data.get('status')},
                status=status.HTTP_200_OK,
            )
        return Response({'detail': 'Paiement confirme et traite'}, status=status.HTTP_200_OK)
