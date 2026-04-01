from django.db import models

from accounts.models import User


class ResidenceZone(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)

    class Meta:
        db_table = 'zones'
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.name} — {self.city}"


class AgentProfile(models.Model):
    APPROVAL_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    PROFESSION_CHOICES = [
        ('nurse_general', 'Infirmier(ère) généraliste'),
        ('nurse_clinical', 'Infirmier(ère) clinicien(ne)'),
        ('nurse_icu', 'Infirmier(ère) aux soins intensifs'),
        ('nurse_emergency', 'Infirmier(ère) urgentiste'),
        ('nurse_psych', 'Infirmier(ère) en santé mentale'),
        ('nurse_pediatric', 'Infirmier(ère) pédiatrique'),
        ('nurse_community', 'Infirmier(ère) communautaire'),
        ('nurse_practitioner', 'Infirmier(ère) praticien(ne)'),
        ('nursing_assistant', 'Aide-soignant(e)'),
        ('nursing_assistant_psych', 'Aide-soignant(e) psychiatrique'),
        ('midwife', 'Sage-femme'),
        ('auxiliary_childcare', 'Auxiliaire de puériculture'),
        ('physiotherapist', 'Kinésithérapeute'),
        ('occupational_therapist', 'Ergothérapeute'),
        ('speech_therapist', 'Orthophoniste'),
        ('nutritionist', 'Diététicien(ne) / nutritionniste'),
        ('medical_doctor', 'Médecin'),
        ('psychologist', 'Psychologue'),
        ('social_worker', 'Assistant(e) social(e)'),
        ('medical_lab_tech', 'Technicien(ne) de laboratoire médical'),
        ('pharmacy_tech', 'Technicien(ne) en pharmacie'),
        ('paramedic', 'Ambulancier(ère) / aide médical urgent'),
        ('dentist', 'Chirurgien(ne)-dentiste'),
        ('medical_technician', 'Technicien(ne) médical(e)'),
        ('caregiver_elderly', 'Accompagnant(e) / auxiliaire de vie'),
        ('other', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    full_name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='agents/avatars/', null=True, blank=True)
    profession = models.CharField(max_length=40, choices=PROFESSION_CHOICES, default='other')
    specialization = models.CharField(max_length=200, blank=True)
    experience_years = models.IntegerField(default=0)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    is_available = models.BooleanField(default=False)
    residence_zone = models.ForeignKey(
        ResidenceZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
    )
    coverage_zones = models.ManyToManyField(
        ResidenceZone,
        blank=True,
        related_name='covering_agents',
        help_text="Zones de résidence que l'agent accepte de couvrir (assignation patient).",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agent_profiles'

    def __str__(self):
        return self.full_name


class AgentDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('national_id', "Pièce d'identité nationale"),
        ('diploma', 'Diplôme'),
        ('license', 'Licence professionnelle'),
        ('other', 'Autre'),
    ]

    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    file = models.FileField(upload_to='agents/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agent_documents'

    def __str__(self):
        return f"{self.agent.full_name} — {self.get_document_type_display()}"


class AgentSchedule(models.Model):
    DAY_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ]

    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = 'agent_schedules'
        unique_together = ('agent', 'day_of_week')

    def __str__(self):
        return f"{self.agent.full_name} — {self.get_day_of_week_display()}"
