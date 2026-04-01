from django.db import models


class AssignmentQueue(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('assigned', 'Assigné'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]

    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='assignment_queues',
    )
    # Snapshot of sorted agent ids at the time matching started
    ordered_agent_ids = models.JSONField(default=list)
    current_index = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_queues'
        ordering = ['-created_at']

    def __str__(self):
        return f"Queue#{self.id} — {self.patient.full_name} [{self.status}]"


class AssignmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Accepté'),
        ('declined', 'Refusé'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
    ]

    queue = models.ForeignKey(
        AssignmentQueue,
        on_delete=models.CASCADE,
        related_name='requests',
    )
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='assignment_requests',
    )
    agent = models.ForeignKey(
        'agents.AgentProfile',
        on_delete=models.CASCADE,
        related_name='assignment_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    # ID of the scheduled Celery timeout task so we can revoke it on accept/decline
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'assignment_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Request#{self.id} — {self.agent.full_name} → {self.patient.full_name} [{self.status}]"
