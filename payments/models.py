from django.db import models

from patients.models import Subscription


class Payment(models.Model):
    METHOD_CHOICES = [
        ('card', 'Carte bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('cash', 'Espèces'),
        ('transfer', 'Virement bancaire'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('success', 'Réussi'),
        ('failed', 'Échoué'),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Paiement #{self.id} — {self.amount} ({self.get_status_display()})"


class DonationTransaction(models.Model):
    DONATION_STATUS = [
        ('pending', 'En attente'),
        ('completed', 'Terminee'),
        ('failed', 'Echouee'),
        ('refunded', 'Remboursee'),
    ]

    PAYMENT_METHODS = [
        ('FLOOZ', 'FLOOZ'),
        ('TMONEY', 'TMONEY'),
    ]

    donor_name = models.CharField(max_length=150, blank=True, default='')
    donor_email = models.EmailField(blank=True, default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=DONATION_STATUS, default='pending')
    identifier = models.CharField(max_length=100, unique=True, blank=True, null=True)
    tx_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'donation_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Don #{self.id} — {self.amount} ({self.get_status_display()})"


class PaygateDonationStatus(models.Model):
    donation = models.OneToOneField(
        DonationTransaction,
        on_delete=models.CASCADE,
        related_name='paygate_status',
    )
    tx_reference = models.CharField(max_length=100, unique=True)
    identifier = models.CharField(max_length=100, unique=True)
    payment_reference = models.CharField(max_length=100, blank=True, default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    datetime = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'paygate_donation_statuses'
        ordering = ['-created_at']
