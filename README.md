# MLACare Backend

## Matching worker cron (sans Celery)

Le matching est traite par une commande Django qui simule un worker.

### Commande

`python manage.py matching_worker_tick`

Cette commande traite:
- expirations de demandes d'assignation (`expires_at`),
- retries dus (`next_retry_at`),
- progression des files en attente.

### Cron chaque minute

Exemple de crontab:

`* * * * * cd /Users/wisdomfoli/Projects/mlacare_project/mlacare_backend && /usr/bin/python3 manage.py matching_worker_tick >> /var/log/mlacare_matching_worker.log 2>&1`

## Assignation JIT des visites

Une commande dediee assigne dynamiquement les agents uniquement pour les visites proches
de l'horaire planifie (dispatch just-in-time).

### Commande

`python manage.py assign_upcoming_visits --window-minutes 60`

Cette commande:
- prend les visites sans agent dans la fenetre temporelle,
- applique le filtrage zone + disponibilite (`is_available=True`) avec fallback global,
- n'assigne jamais deux fois la meme visite (idempotent/concurrent-safe).

### Cron chaque minute

Exemple de crontab:

`* * * * * cd /Users/wisdomfoli/Projects/mlacare_project/mlacare_backend && /usr/bin/python3 manage.py assign_upcoming_visits --window-minutes 60 >> /var/log/mlacare_visit_dispatch.log 2>&1`

### Supervision minimale

- Verifier les logs: `rg "ERROR|Traceback" /var/log/mlacare_matching_worker.log`
- Mettre en place une rotation de logs (logrotate) pour ce fichier.

## Deploiement production (O2switch)

L'hebergement mutualise O2switch utilise **Phusion Passenger** et un fichier **WSGI**. La racine de l'application Python (`Application root` dans cPanel) doit etre le dossier qui contient `manage.py` (ce depot), **pas** le dossier `public_html` du domaine.

### 1. Setup Python App (cPanel)

1. **Create Application** : choisir Python **3.10+** (compatible Django 5.2 ; 3.11 est souvent propose).
2. **Application root** : chemin vers les sources (ex. `~/mlacare_backend`).
3. **Application URL** : sous-domaine ou domaine dedie a l'API (ex. `api.votredomaine.fr`).
4. **Application startup file** : `passenger_wsgi.py` ou `mlacare/wsgi.py`.
5. **Application entry point** : `application`.
6. Ajouter les variables d'environnement (voir `.env.example`) via **Add Variable**, ou un fichier charge par votre workflow.

### 2. Installation

Dans le terminal cPanel (apres `source` du virtualenv indique par l'outil) :

```bash
cd ~/mlacare_backend
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Creer le repertoire media si besoin : `mkdir -p media` (droits d'ecriture pour l'app).

### 3. Variables obligatoires en production

- `DEBUG=False`
- `DJANGO_SECRET_KEY` : cle longue et aleatoire (jamais la cle de developpement).
- `ALLOWED_HOSTS` : votre domaine API.
- `CORS_ALLOWED_ORIGINS` : URL(s) du front (HTTPS).
- `CSRF_TRUSTED_ORIGINS` : memes origines en `https://...` si vous utilisez l'admin ou des vues sensibles au CSRF.
- Base **PostgreSQL** : `PG*` (O2switch peut proposer PostgreSQL selon l'offre ; sinon base externe).
- `SERVE_MEDIA_VIA_DJANGO=True` pour servir les fichiers uploades via Django (recommande sur mutualise si vous n'avez pas d'alias Apache vers `media/`).

Puis **Restart** l'application dans Setup Python App.

### 4. Cron matching worker

Remplacer le chemin par votre `Application root` et le Python du venv O2switch :

`* * * * * cd /home/VOTRE_USER/mlacare_backend && /home/VOTRE_USER/virtualenv/.../bin/python manage.py matching_worker_tick >> ~/logs/mlacare_matching_worker.log 2>&1`

### 5. Depannage

- Consulter le **Passenger log file** indique dans cPanel.
- Erreur 500 au demarrage : verifier `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, et la connexion PostgreSQL.
- Fichiers statiques admin : verifier que `collectstatic` a bien ete execute et que **WhiteNoise** est actif (deja configure dans `settings.py`).
