import json
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from common.db_fixture import DEFAULT_FIXTURE_PATH, FIXTURE_LABELS


class Command(BaseCommand):
    help = (
        'Exporte les données métier de la base connectée vers une fixture JSON '
        '(usage typique : lancer sur la prod, puis charger en local).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            '-o',
            default=str(DEFAULT_FIXTURE_PATH),
            help=f'Chemin du fichier JSON (défaut : {DEFAULT_FIXTURE_PATH}).',
        )
        parser.add_argument(
            '--indent',
            type=int,
            default=2,
            help='Indentation JSON (défaut : 2, 0 pour compact).',
        )

    def handle(self, *args, **options):
        output_path = Path(options['output']).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        indent = options['indent']
        dump_kwargs = {
            'format': 'json',
            'natural_foreign': True,
            'natural_primary': True,
            'output': str(output_path),
        }
        if indent:
            dump_kwargs['indent'] = indent

        db = settings.DATABASES['default']
        db_label = f"{db['HOST']}:{db['PORT']}/{db['NAME']}"
        self.stdout.write(f'Export depuis {db_label} vers {output_path} …')

        try:
            call_command('dumpdata', *FIXTURE_LABELS, **dump_kwargs)
        except Exception as exc:
            raise CommandError(f'Échec de dumpdata : {exc}') from exc

        if not output_path.exists():
            raise CommandError(
                f'Échec : le fichier {output_path} n\'a pas été créé.'
            )

        object_count = self._count_objects(output_path)
        self.stdout.write(
            self.style.SUCCESS(
                f'Fixture écrite : {output_path} ({object_count} enregistrements).'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'Les fichiers media/ (avatars, documents) ne sont pas inclus. '
                'Copiez le dossier media/ séparément si nécessaire.'
            )
        )

    @staticmethod
    def _count_objects(path: Path) -> int:
        with path.open(encoding='utf-8') as handle:
            payload = json.load(handle)
        return len(payload) if isinstance(payload, list) else 0
