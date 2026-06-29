from pathlib import Path

from django.conf import settings

# Modèles métier exportés (ordre indicatif ; dumpdata gère les dépendances).
FIXTURE_LABELS = [
    'contenttypes.contenttype',
    'auth.permission',
    'accounts.user',
    'agents.residencezone',
    'agents.agentprofile',
    'patients.plan',
    'patients.patientprofile',
    'patients.subscription',
    'agents.agentdocument',
    'agents.agentschedule',
    'visits.visit',
    'visits.visitprescreening',
    'visits.vitalsigns',
    'visits.healthreport',
    'visits.reportattachment',
    'visits.visitreview',
    'notifications.notification',
    'notifications.sosalert',
    'payments.payment',
    'payments.donationtransaction',
    'payments.paygatedonationstatus',
    'admin_api.adminsetting',
]

# Données éphémères ou régénérables — exclues volontairement.
EXCLUDED_LABELS = [
    'sessions.session',
    'token_blacklist.outstandingtoken',
    'token_blacklist.blacklistedtoken',
    'accounts.otpverification',
    'admin.logentry',
]

DEFAULT_FIXTURE_PATH = Path(settings.BASE_DIR) / 'fixtures' / 'prod_snapshot.json'
