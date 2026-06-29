from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from common.db_fixture import DEFAULT_FIXTURE_PATH


class Command(BaseCommand):
    help = (
        'Charge une fixture JSON exportée (ex. snapshot prod) dans la base locale. '
        'Par défaut, refuse de s\'exécuter sur une base distante.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            '-i',
            default=str(DEFAULT_FIXTURE_PATH),
            help=f'Chemin du fichier JSON (défaut : {DEFAULT_FIXTURE_PATH}).',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Vide la base avant le chargement (recommandé en local).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Autorise le chargement même si USE_LOCAL_DB=False (dangereux).',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input']).resolve()
        if not input_path.exists():
            raise CommandError(f'Fixture introuvable : {input_path}')

        if not settings.USE_LOCAL_DB and not options['force']:
            raise CommandError(
                'Refus de charger une fixture sur une base distante '
                '(USE_LOCAL_DB=False). Utilisez --force uniquement si vous '
                'savez ce que vous faites.'
            )

        db = settings.DATABASES['default']
        db_label = f"{db['HOST']}:{db['PORT']}/{db['NAME']}"

        if options['flush']:
            self.stdout.write(self.style.WARNING(f'Vidage de {db_label} …'))
            call_command('flush', '--noinput')

        self.stdout.write(f'Chargement de {input_path} dans {db_label} …')
        try:
            call_command('loaddata', str(input_path))
        except Exception as exc:
            raise CommandError(f'Échec de loaddata : {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Fixture chargée avec succès.'))
        self.stdout.write(
            'Pensez à copier media/ depuis la prod si vous avez besoin '
            'des avatars et documents uploadés.'
        )
