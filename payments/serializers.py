from rest_framework import serializers

from patients.serializers import SubscriptionSerializer

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    subscription_detail = SubscriptionSerializer(source='subscription', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    method_label = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'subscription', 'subscription_detail',
            'amount', 'payment_method', 'method_label',
            'status', 'status_label',
            'transaction_id', 'paid_at', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'status_label', 'method_label', 'paid_at', 'created_at']

    def validate(self, attrs):
        subscription = attrs.get('subscription')
        amount = attrs.get('amount')
        transaction_id = attrs.get('transaction_id')
        payment_method = attrs.get('payment_method')
        user = self.context['request'].user

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({'amount': 'Le montant doit être supérieur à 0.'})

        if user.role == 'patient' and subscription and subscription.patient.user_id != user.id:
            raise serializers.ValidationError({'subscription': "Vous ne pouvez payer que votre propre abonnement."})

        if payment_method in ('card', 'mobile_money', 'transfer') and not transaction_id:
            raise serializers.ValidationError(
                {'transaction_id': "L'identifiant de transaction est requis pour ce mode de paiement."}
            )
        return attrs
