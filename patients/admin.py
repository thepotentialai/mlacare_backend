from django.contrib import admin

from .models import PatientProfile, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'visits_per_month', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'city', 'zone', 'created_at']
    search_fields = ['full_name', 'city']
    list_filter = ['gender', 'city']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'plan', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'plan']
    search_fields = ['patient__full_name']
