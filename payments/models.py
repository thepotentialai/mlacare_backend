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
