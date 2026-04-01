from django.contrib import admin

from matching.models import AssignmentQueue, AssignmentRequest


@admin.register(AssignmentQueue)
class AssignmentQueueAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'status', 'current_index', 'retry_count', 'created_at']
    list_filter = ['status']
    readonly_fields = ['ordered_agent_ids', 'created_at', 'updated_at']
    search_fields = ['patient__full_name']


@admin.register(AssignmentRequest)
class AssignmentRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'agent', 'status', 'expires_at', 'created_at', 'responded_at']
    list_filter = ['status']
    readonly_fields = ['celery_task_id', 'created_at', 'responded_at']
    search_fields = ['patient__full_name', 'agent__full_name']
