import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlacare.settings')

app = Celery('mlacare')

# Charger la config depuis Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les apps Django
app.autodiscover_tasks()
