from rest_framework import serializers

from patients.serializers import SubscriptionSerializer

from .models import DonationTransaction, Payment


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


class DonationTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationTransaction
        fields = '__all__'
        read_only_fields = ['id', 'status', 'identifier', 'tx_reference', 'created_at', 'updated_at']


class DonationInitSerializer(serializers.Serializer):
    DONATION_FREQUENCY = [
        ('one_time', 'Don unique'),
        ('monthly', 'Don mensuel'),
    ]

    donor_name = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    donor_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    phone_number = serializers.CharField(max_length=20)
    payment_method = serializers.ChoiceField(choices=DonationTransaction.PAYMENT_METHODS)
    donation_frequency = serializers.ChoiceField(choices=DONATION_FREQUENCY, default='one_time')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Le montant doit être supérieur à 0.')
        return value


class PaygateCallbackSerializer(serializers.Serializer):
    tx_reference = serializers.CharField(max_length=100)
    identifier = serializers.CharField(max_length=100)
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    datetime = serializers.DateTimeField(required=False, allow_null=True)
    payment_method = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        cleaned_data = {}
        for key, value in data.items():
            if value == '' or (isinstance(value, str) and value.strip() == ''):
                cleaned_data[key] = None
            elif isinstance(value, list) and len(value) > 0:
                cleaned_data[key] = value[0] if len(value) == 1 else value
            elif isinstance(value, list) and len(value) == 0:
                cleaned_data[key] = None
            else:
                cleaned_data[key] = value

        if 'datetime' in cleaned_data and cleaned_data['datetime']:
            dt = str(cleaned_data['datetime']).strip()
            if dt.endswith(' UTC'):
                dt = dt.replace(' UTC', 'Z')
                if ' ' in dt and 'T' not in dt:
                    dt = dt.replace(' ', 'T', 1)
                cleaned_data['datetime'] = dt

        return super().to_internal_value(cleaned_data)
