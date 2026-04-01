from rest_framework import serializers

from .models import PatientProfile, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'description', 'price', 'visits_per_month', 'features', 'is_active']
        read_only_fields = ['id']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True),
        source='plan',
        write_only=True,
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'plan_id', 'start_date', 'end_date', 'status', 'status_label', 'created_at']
        read_only_fields = ['id', 'start_date', 'end_date', 'status', 'status_label', 'created_at']


class PatientProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    zone_name = serializers.SerializerMethodField()
    current_subscription = serializers.SerializerMethodField()

    class Meta:
        model = PatientProfile
        fields = [
            'id', 'email', 'phone', 'full_name', 'date_of_birth', 'gender', 'avatar',
            'address', 'city', 'zone', 'zone_name',
            'emergency_contact_name', 'emergency_contact_phone',
            'health_notes', 'current_subscription',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'phone', 'created_at', 'updated_at']

    def get_zone_name(self, obj):
        return f"{obj.zone.name} — {obj.zone.city}" if obj.zone else None

    def get_current_subscription(self, obj):
        sub = obj.subscriptions.filter(status='active').first()
        return SubscriptionSerializer(sub).data if sub else None
