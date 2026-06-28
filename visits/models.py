from django.db import models

from agents.models import AgentProfile
from patients.models import PatientProfile, Subscription


class Visit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('absent', 'Patient absent'),
        ('rescheduled', 'Reportée'),
        ('cancelled', 'Annulé'),
    ]

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='visits')
    agent = models.ForeignKey(
        AgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits'
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits'
    )
    visit_number = models.PositiveIntegerField(null=True, blank=True, verbose_name='Numéro de visite du cycle')
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    address = models.TextField()
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rescheduled_from = models.DateTimeField(null=True, blank=True, verbose_name='Date originale avant report')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visits'
        ordering = ['-scheduled_date', '-scheduled_time']

    def __str__(self):
        return f"Visite #{self.id} — {self.patient.display_name} ({self.status})"


class VisitPreScreening(models.Model):
    """Questionnaire court avant la saisie des signes vitaux (à jeun, douleur, traitements)."""

    FASTING_YES = 'yes'
    FASTING_NO = 'no'
    FASTING_UNKNOWN = 'unknown'
    FASTING_CHOICES = [
        (FASTING_YES, 'À jeun'),
        (FASTING_NO, "Pas à jeun"),
        (FASTING_UNKNOWN, 'Ne sait pas'),
    ]

    MED_NA = 'na'
    MED_YES = 'yes'
    MED_NO = 'no'
    MED_PARTIAL = 'partial'
    MEDICATIONS_TAKEN_CHOICES = [
        (MED_NA, 'Sans objet'),
        (MED_YES, 'Oui, pris comme prévu'),
        (MED_NO, 'Non'),
        (MED_PARTIAL, 'Partiellement'),
    ]

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='pre_screening')
    fasting_status = models.CharField(max_length=10, choices=FASTING_CHOICES)
    has_pain = models.BooleanField()
    pain_description = models.TextField(blank=True)
    takes_medications = models.BooleanField()
    medications_taken_status = models.CharField(max_length=10, choices=MEDICATIONS_TAKEN_CHOICES)
    medication_names = models.TextField(blank=True)
    extra_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visit_pre_screenings'

    def __str__(self):
        return f"Questionnaire pré-visite — Visite #{self.visit_id}"

    def is_complete(self) -> bool:
        if not self.fasting_status:
            return False
        if self.has_pain and not (self.pain_description or '').strip():
            return False
        if self.takes_medications:
            if self.medications_taken_status not in (
                self.MED_YES,
                self.MED_NO,
                self.MED_PARTIAL,
            ):
                return False
            if not (self.medication_names or '').strip():
                return False
        elif self.medications_taken_status != self.MED_NA:
            return False
        return True


class VitalSigns(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='vital_signs')
    blood_pressure_sys = models.IntegerField(null=True, blank=True, verbose_name='Tension systolique (mmHg)')
    blood_pressure_dia = models.IntegerField(null=True, blank=True, verbose_name='Tension diastolique (mmHg)')
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='Fréquence cardiaque (bpm)')
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Température (°C)')
    respiratory_rate = models.IntegerField(null=True, blank=True, verbose_name='Fréquence respiratoire (/min)')
    spo2 = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='SpO2 (%)')
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Glycémie (mmol/L)')
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Poids (kg)')
    height = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Taille (cm)')
    symptoms = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    is_urgent = models.BooleanField(default=False)
    referral_needed = models.BooleanField(default=False)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vital_signs'

    def __str__(self):
        return f"Signes vitaux — Visite #{self.visit_id}"


class HealthReport(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='health_reports')
    visit = models.ForeignKey(
        Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='health_reports'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'health_reports'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ReportAttachment(models.Model):
    report = models.ForeignKey(HealthReport, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='health_reports/attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_attachments'

    def __str__(self):
        return f"Pièce jointe — {self.report.title}"


class VisitReview(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visit_reviews'

    def __str__(self):
        if self.skipped:
            return f"Avis ignoré — Visite #{self.visit_id}"
        return f"Avis {self.rating}/5 — Visite #{self.visit_id}"
