from rest_framework import serializers

from .models import Notification, SOSAlert


class NotificationSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'type_label', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at', 'type_label']


class SOSAlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:
        model = SOSAlert
        fields = [
            'id', 'patient_name', 'latitude', 'longitude', 'message',
            'is_resolved', 'resolved_at', 'created_at',
        ]
        read_only_fields = ['id', 'patient_name', 'is_resolved', 'resolved_at', 'created_at']
