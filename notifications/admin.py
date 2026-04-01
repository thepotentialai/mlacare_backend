from django.contrib import admin

from .models import Notification, SOSAlert


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
    search_fields = ['title', 'user__email']


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ['patient', 'is_resolved', 'created_at', 'resolved_at']
    list_filter = ['is_resolved']
    search_fields = ['patient__full_name']
