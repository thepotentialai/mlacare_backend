from django.contrib import admin

from .models import AgentDocument, AgentProfile, AgentSchedule, ResidenceZone


@admin.register(ResidenceZone)
class ResidenceZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'city']
    search_fields = ['name', 'city']


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'profession', 'specialization', 'approval_status', 'is_available', 'created_at']
    list_filter = ['approval_status', 'is_available', 'profession']
    search_fields = ['full_name', 'specialization', 'profession']
    actions = ['approve_agents', 'reject_agents']

    @admin.action(description='Approuver les agents sélectionnés')
    def approve_agents(self, request, queryset):
        queryset.update(approval_status='approved')

    @admin.action(description='Rejeter les agents sélectionnés')
    def reject_agents(self, request, queryset):
        queryset.update(approval_status='rejected')


@admin.register(AgentDocument)
class AgentDocumentAdmin(admin.ModelAdmin):
    list_display = ['agent', 'document_type', 'uploaded_at']


@admin.register(AgentSchedule)
class AgentScheduleAdmin(admin.ModelAdmin):
    list_display = ['agent', 'day_of_week', 'start_time', 'end_time']
