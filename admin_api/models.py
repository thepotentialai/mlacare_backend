from django.db import models


class AdminSetting(models.Model):
    """Key-value store for admin-configurable application settings."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_settings'
        ordering = ['key']

    def __str__(self):
        return f"{self.key} = {self.value}"
