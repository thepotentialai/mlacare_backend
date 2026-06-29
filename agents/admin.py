from django.contrib import admin

from .approval import approve_agent
from .models import AgentDocument, AgentProfile, AgentSchedule, ResidenceZone


@admin.register(ResidenceZone)
class ResidenceZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'city']
    search_fields = ['name', 'city']


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'profession', 'specialization', 'nif', 'approval_status', 'is_available', 'created_at']
    list_filter = ['approval_status', 'is_available', 'profession']
    search_fields = ['first_name', 'last_name', 'specialization', 'profession', 'nif']
    actions = ['approve_agents']

    @admin.action(description='Approuver les agents sélectionnés')
    def approve_agents(self, request, queryset):
        for agent in queryset:
            if agent.approval_status in ('pending', 'rejected'):
                approve_agent(agent, by_user=request.user)


@admin.register(AgentDocument)
class AgentDocumentAdmin(admin.ModelAdmin):
    list_display = ['agent', 'document_type', 'uploaded_at']


@admin.register(AgentSchedule)
class AgentScheduleAdmin(admin.ModelAdmin):
    list_display = ['agent', 'day_of_week', 'start_time', 'end_time']
