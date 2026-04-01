from django.contrib import admin

from .models import HealthReport, ReportAttachment, Visit, VitalSigns


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'agent', 'scheduled_date', 'scheduled_time', 'status']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['patient__full_name', 'agent__full_name']
    date_hierarchy = 'scheduled_date'


@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ['visit', 'heart_rate', 'temperature', 'spo2', 'is_urgent', 'recorded_at']
    list_filter = ['is_urgent', 'referral_needed']


@admin.register(HealthReport)
class HealthReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'patient', 'visit', 'created_at']
    search_fields = ['title', 'patient__full_name']


@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ['report', 'uploaded_at']
