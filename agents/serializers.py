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
    pending_residence_zone = ResidenceZoneSerializer(read_only=True)
    pending_coverage_zones = ResidenceZoneSerializer(many=True, read_only=True)
    zones_pending_review = serializers.SerializerMethodField()
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
            'profession', 'profession_label', 'specialization', 'nif', 'experience_years',
            'approval_status', 'approval_status_label', 'is_available',
            'residence_zone', 'residence_zone_id',
            'coverage_zones', 'coverage_zone_ids',
            'pending_residence_zone', 'pending_coverage_zones', 'zones_pending_review',
            'latitude', 'longitude', 'schedules', 'documents',
            'average_rating', 'total_reviews',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'phone', 'approval_status', 'created_at', 'updated_at']

    def get_zones_pending_review(self, obj):
        return obj.pending_residence_zone_id is not None or obj.pending_coverage_zones.exists()

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
        request = self.context.get('request')
        is_admin = bool(
            request
            and request.user.is_authenticated
            and (getattr(request.user, 'role', '') == 'admin' or request.user.is_staff)
        )
        coverage = validated_data.pop('coverage_zone_ids', None)
        residence = validated_data.pop('residence_zone', serializers.empty)

        if is_admin:
            instance = super().update(instance, validated_data)
            if residence is not serializers.empty:
                instance.residence_zone = residence
                instance.save(update_fields=['residence_zone', 'updated_at'])
            if coverage is not None:
                instance.coverage_zones.set(coverage)
            return instance

        instance = super().update(instance, validated_data)

        if coverage is None and residence is serializers.empty:
            return instance

        cur_cov_ids = sorted(instance.coverage_zones.values_list('pk', flat=True))
        new_cov_ids = sorted(z.pk for z in coverage) if coverage is not None else None

        if residence is serializers.empty:
            res_changed = False
        else:
            new_rid = residence.pk if residence is not None else None
            res_changed = instance.residence_zone_id != new_rid

        cov_changed = new_cov_ids is not None and new_cov_ids != cur_cov_ids
        if not res_changed and not cov_changed:
            return instance

        pending_res = instance.residence_zone if residence is serializers.empty else residence
        instance.pending_residence_zone = pending_res
        instance.save(update_fields=['pending_residence_zone', 'updated_at'])
        if coverage is not None:
            instance.pending_coverage_zones.set(coverage)
        else:
            instance.pending_coverage_zones.set(cur_cov_ids)
        return instance
