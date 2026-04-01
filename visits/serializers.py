from rest_framework import serializers

from .models import HealthReport, ReportAttachment, Visit, VitalSigns, VisitReview
from .services import assign_agent_to_visit


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = ['id', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class VitalSignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSigns
        fields = [
            'id',
            'blood_pressure_sys', 'blood_pressure_dia',
            'heart_rate', 'temperature', 'respiratory_rate', 'spo2',
            'blood_glucose', 'weight', 'height',
            'symptoms', 'observations',
            'is_urgent', 'referral_needed',
            'recorded_at',
        ]
        read_only_fields = ['id', 'recorded_at']


class VisitReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitReview
        fields = ['id', 'rating', 'comment', 'skipped', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        skipped = data.get('skipped', False)
        rating = data.get('rating')
        if not skipped and rating is None:
            raise serializers.ValidationError({'rating': "Une note est requise si vous ne passez pas."})
        if not skipped and rating is not None and not (1 <= rating <= 5):
            raise serializers.ValidationError({'rating': "La note doit être comprise entre 1 et 5."})
        return data


class VisitSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    agent_name = serializers.SerializerMethodField()
    vital_signs = VitalSignsSerializer(read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    review = VisitReviewSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'patient', 'patient_name', 'agent', 'agent_name',
            'subscription', 'visit_number',
            'scheduled_date', 'scheduled_time',
            'status', 'status_label',
            'address', 'notes',
            'vital_signs',
            'review',
            'completed_at',
            'rescheduled_from',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'patient', 'subscription', 'visit_number', 'completed_at', 'rescheduled_from', 'created_at', 'updated_at']

    def get_agent_name(self, obj):
        return obj.agent.full_name if obj.agent else None

    def create(self, validated_data):
        validated_data.pop('agent', None)
        visit = super().create(validated_data)
        assign_agent_to_visit(visit)
        return visit

    def update(self, instance, validated_data):
        if 'agent' in validated_data:
            agent = validated_data['agent']
            if agent is not None:
                zone = instance.patient.zone
                if zone and not agent.coverage_zones.filter(pk=zone.pk).exists():
                    raise serializers.ValidationError(
                        {
                            'agent': "Cet agent ne couvre pas la zone de résidence du patient.",
                        },
                    )
        return super().update(instance, validated_data)


class HealthReportSerializer(serializers.ModelSerializer):
    attachments = ReportAttachmentSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:
        model = HealthReport
        fields = ['id', 'patient', 'patient_name', 'visit', 'title', 'content', 'attachments', 'created_at']
        read_only_fields = ['id', 'patient', 'created_at']
