from django.db import models

from accounts.models import User
from patients.models import PatientProfile


class Notification(models.Model):
    TYPE_CHOICES = [
        ('visit', 'Visite'),
        ('payment', 'Paiement'),
        ('system', 'Système'),
        ('alert', 'Alerte'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.user.email}"


class SOSAlert(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='sos_alerts')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    message = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sos_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"SOS — {self.patient.full_name} ({'résolu' if self.is_resolved else 'actif'})"
