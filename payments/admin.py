from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscription', 'amount', 'payment_method', 'status', 'paid_at', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['subscription__patient__full_name', 'transaction_id']
    date_hierarchy = 'created_at'
