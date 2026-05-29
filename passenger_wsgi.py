"""
Point d'entrée WSGI pour Phusion Passenger (cPanel / O2switch « Setup Python App »).

Si l'interface demande le fichier de démarrage à la racine du projet, utilisez :
  passenger_wsgi.py
avec le point d'entrée : application

Sinon : mlacare/wsgi.py (même callable).
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlacare.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
