from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers

from agents.models import AgentProfile, ResidenceZone
from .models import OTPVerification, User


class RegisterPatientSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=200)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=['male', 'female', 'other'], required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zone_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Un compte avec ce numéro existe déjà.")
        return value

    def create(self, validated_data):
        profile_data = {
            'full_name': validated_data.pop('full_name'),
            'date_of_birth': validated_data.pop('date_of_birth', None),
            'gender': validated_data.pop('gender', ''),
            'address': validated_data.pop('address', ''),
            'city': validated_data.pop('city', ''),
            'zone_id': validated_data.pop('zone_id', None),
        }
        user = User.objects.create_user(role='patient', **validated_data)

        from patients.models import PatientProfile
        PatientProfile.objects.create(user=user, **profile_data)
        return user


class RegisterAgentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=200)
    profession = serializers.ChoiceField(choices=AgentProfile.PROFESSION_CHOICES)
    specialization = serializers.CharField(max_length=200, required=False, allow_blank=True)
    experience_years = serializers.IntegerField(min_value=0)
    residence_zone_id = serializers.IntegerField(required=False, allow_null=True)
    # Backward-compatible payload (old "zone de service" list)
    zone_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Un compte avec ce numéro existe déjà.")
        return value

    def create(self, validated_data):
        residence_zone_id = validated_data.pop('residence_zone_id', None)
        zone_ids = validated_data.pop('zone_ids', [])
        profile_data = {
            'full_name': validated_data.pop('full_name'),
            'profession': validated_data.pop('profession'),
            'specialization': (validated_data.pop('specialization', '') or '').strip(),
            'experience_years': validated_data.pop('experience_years'),
        }

        with transaction.atomic():
            user = User.objects.create_user(role='agent', **validated_data)

            # Prefer new payload; fallback to first entry in legacy list if provided
            if residence_zone_id is None and zone_ids:
                residence_zone_id = zone_ids[0]

            profile = AgentProfile.objects.create(user=user, **profile_data)
            coverage_ids = list(dict.fromkeys(zone_ids)) if zone_ids else []
            if residence_zone_id is not None:
                try:
                    rz = ResidenceZone.objects.get(id=residence_zone_id)
                    profile.residence_zone = rz
                    profile.save(update_fields=['residence_zone'])
                    if not coverage_ids:
                        coverage_ids = [residence_zone_id]
                    else:
                        coverage_ids = list(dict.fromkeys([*coverage_ids, residence_zone_id]))
                except ResidenceZone.DoesNotExist:
                    pass
            if coverage_ids:
                zones = ResidenceZone.objects.filter(id__in=coverage_ids)
                profile.coverage_zones.set(zones)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        data['user'] = user
        return data


class OTPVerifySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    code = serializers.CharField(max_length=6)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'role', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'role', 'is_verified', 'date_joined']
