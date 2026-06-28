from django.contrib import admin

from .models import DonationTransaction, Payment, PaygateDonationStatus


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscription', 'amount', 'payment_method', 'status', 'paid_at', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['subscription__patient__first_name', 'subscription__patient__last_name', 'transaction_id']
    date_hierarchy = 'created_at'


@admin.register(DonationTransaction)
class DonationTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'donor_name', 'donor_email', 'amount', 'payment_method',
        'status', 'identifier', 'tx_reference', 'created_at',
    ]
    list_filter = ['status', 'payment_method']
    search_fields = ['donor_name', 'donor_email', 'identifier', 'tx_reference', 'phone_number']
    date_hierarchy = 'created_at'


@admin.register(PaygateDonationStatus)
class PaygateDonationStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'donation', 'tx_reference', 'identifier', 'payment_reference', 'created_at']
    search_fields = ['tx_reference', 'identifier', 'payment_reference', 'phone_number']
    date_hierarchy = 'created_at'
