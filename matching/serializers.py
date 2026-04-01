from rest_framework import serializers

from matching.models import AssignmentQueue, AssignmentRequest


class AssignmentRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_zone = serializers.SerializerMethodField()
    patient_city = serializers.SerializerMethodField()
    patient_address = serializers.CharField(source='patient.address', read_only=True)
    patient_health_notes = serializers.CharField(source='patient.health_notes', read_only=True)
    agent_name = serializers.CharField(source='agent.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    def get_patient_zone(self, obj):
        return obj.patient.zone.name if obj.patient.zone else None

    def get_patient_city(self, obj):
        return obj.patient.zone.city if obj.patient.zone else None

    class Meta:
        model = AssignmentRequest
        fields = [
            'id', 'queue', 'patient', 'patient_name', 'patient_zone', 'patient_city',
            'patient_address', 'patient_health_notes',
            'agent', 'agent_name',
            'status', 'status_display',
            'expires_at', 'created_at', 'responded_at',
        ]
        read_only_fields = fields


class AssignmentQueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requests = AssignmentRequestSerializer(many=True, read_only=True)

    class Meta:
        model = AssignmentQueue
        fields = [
            'id', 'patient', 'patient_name',
            'ordered_agent_ids', 'current_index',
            'status', 'status_display',
            'retry_count', 'created_at', 'updated_at',
            'requests',
        ]
        read_only_fields = fields
