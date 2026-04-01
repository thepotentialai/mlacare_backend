from django.db.models import Avg

from rest_framework import serializers

from .models import AgentDocument, AgentProfile, AgentSchedule, ResidenceZone


class ResidenceZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidenceZone
        fields = ['id', 'name', 'city']


class AgentScheduleSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = AgentSchedule
        fields = ['id', 'day_of_week', 'day_label', 'start_time', 'end_time']
        read_only_fields = ['id', 'day_label']

    def validate(self, attrs):
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError({'end_time': "L'heure de fin doit être après l'heure de début."})
        return attrs


class AgentDocumentSerializer(serializers.ModelSerializer):
    document_type_label = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = AgentDocument
        fields = ['id', 'document_type', 'document_type_label', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'document_type_label']


class AgentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    schedules = AgentScheduleSerializer(many=True, read_only=True)
    approval_status_label = serializers.CharField(source='get_approval_status_display', read_only=True)
    profession_label = serializers.CharField(source='get_profession_display', read_only=True)
    residence_zone = ResidenceZoneSerializer(read_only=True)
    coverage_zones = ResidenceZoneSerializer(many=True, read_only=True)
    documents = AgentDocumentSerializer(many=True, read_only=True)
    residence_zone_id = serializers.PrimaryKeyRelatedField(
        queryset=ResidenceZone.objects.all(),
        source='residence_zone',
        write_only=True,
        required=False,
        allow_null=True,
    )
    coverage_zone_ids = serializers.PrimaryKeyRelatedField(
        queryset=ResidenceZone.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfile
        fields = [
            'id', 'email', 'phone', 'full_name', 'bio', 'avatar',
            'profession', 'profession_label', 'specialization', 'experience_years',
            'approval_status', 'approval_status_label', 'is_available',
            'residence_zone', 'residence_zone_id',
            'coverage_zones', 'coverage_zone_ids',
            'latitude', 'longitude', 'schedules', 'documents',
            'average_rating', 'total_reviews',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'phone', 'approval_status', 'created_at', 'updated_at']

    def get_average_rating(self, obj):
        from visits.models import VisitReview
        agg = VisitReview.objects.filter(
            visit__agent=obj, skipped=False, rating__isnull=False
        ).aggregate(avg=Avg('rating'))
        return round(agg['avg'], 1) if agg['avg'] is not None else None

    def get_total_reviews(self, obj):
        from visits.models import VisitReview
        return VisitReview.objects.filter(
            visit__agent=obj, skipped=False, rating__isnull=False
        ).count()

    def update(self, instance, validated_data):
        coverage = validated_data.pop('coverage_zone_ids', None)
        instance = super().update(instance, validated_data)
        if coverage is not None:
            instance.coverage_zones.set(coverage)
        return instance
