from rest_framework import serializers

from .models import HealthReport, ReportAttachment, Visit, VisitPreScreening, VitalSigns, VisitReview


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = ['id', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class VisitPreScreeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitPreScreening
        fields = [
            'id',
            'fasting_status',
            'has_pain',
            'pain_description',
            'takes_medications',
            'medications_taken_status',
            'medication_names',
            'extra_notes',
            'recorded_at',
        ]
        read_only_fields = ['id', 'recorded_at']

    def validate(self, data):
        has_pain = data.get('has_pain')
        if has_pain is None:
            raise serializers.ValidationError({'has_pain': 'Ce champ est obligatoire.'})
        pain_description = (data.get('pain_description') or '').strip()
        if has_pain and not pain_description:
            raise serializers.ValidationError(
                {'pain_description': 'Précisez la localisation ou la nature de la douleur.'},
            )

        takes_medications = data.get('takes_medications')
        if takes_medications is None:
            raise serializers.ValidationError({'takes_medications': 'Ce champ est obligatoire.'})

        med_status = data.get('medications_taken_status')
        med_names = (data.get('medication_names') or '').strip()

        if takes_medications:
            if med_status not in (
                VisitPreScreening.MED_YES,
                VisitPreScreening.MED_NO,
                VisitPreScreening.MED_PARTIAL,
            ):
                raise serializers.ValidationError(
                    {
                        'medications_taken_status': (
                            'Indiquez si les médicaments ont été pris (oui, non ou partiellement).'
                        ),
                    },
                )
            if not med_names:
                raise serializers.ValidationError(
                    {'medication_names': 'Indiquez le nom des médicaments ou du traitement.'},
                )
        else:
            if med_status != VisitPreScreening.MED_NA:
                raise serializers.ValidationError(
                    {
                        'medications_taken_status': (
                            "Sans traitement régulier, choisissez « Sans objet »."
                        ),
                    },
                )
        return data


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
    patient_health_notes = serializers.CharField(source='patient.health_notes', read_only=True)
    agent_name = serializers.SerializerMethodField()
    agent_phone = serializers.SerializerMethodField()
    vital_signs = VitalSignsSerializer(read_only=True)
    pre_screening = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    review = VisitReviewSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'patient', 'patient_name', 'patient_health_notes', 'agent', 'agent_name', 'agent_phone',
            'subscription', 'visit_number',
            'scheduled_date', 'scheduled_time',
            'status', 'status_label',
            'address', 'notes',
            'vital_signs',
            'pre_screening',
            'review',
            'completed_at',
            'rescheduled_from',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'patient', 'subscription', 'visit_number', 'completed_at', 'rescheduled_from', 'created_at', 'updated_at']

    def get_agent_name(self, obj):
        return obj.agent.full_name if obj.agent else None

    def get_agent_phone(self, obj):
        if not obj.agent:
            return None
        return getattr(obj.agent.user, 'phone', None)

    def get_pre_screening(self, obj):
        try:
            ps = obj.pre_screening
        except VisitPreScreening.DoesNotExist:
            return None
        return VisitPreScreeningSerializer(ps).data

    def create(self, validated_data):
        validated_data.pop('agent', None)
        return super().create(validated_data)

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
