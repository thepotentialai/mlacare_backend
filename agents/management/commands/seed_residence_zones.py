from django.core.management.base import BaseCommand

from agents.models import ResidenceZone


DEFAULT_RESIDENCE_ZONES = [
    ("Kodjoviakope", "Lome"),
    ("Nyekonakpoe", "Lome"),
    ("Be", "Lome"),
    ("Adidogome", "Lome"),
    ("Agoe", "Lome"),
    ("Hedzranawoe", "Lome"),
    ("Ablogame", "Lome"),
    ("Kpota", "Aneho"),
    ("Zongo", "Atakpame"),
    ("Komah", "Atakpame"),
    ("Kpangalam", "Sokode"),
    ("Komah Bas", "Sokode"),
]


class Command(BaseCommand):
    help = "Seed default residence zones for patient/agent registration."

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0
        duplicate_count = 0
        kept_zone_ids = []

        for name, city in DEFAULT_RESIDENCE_ZONES:
            matches = ResidenceZone.objects.filter(name=name, city=city).order_by("id")
            zone = matches.first()

            if zone is None:
                zone = ResidenceZone.objects.create(name=name, city=city)
                created_count += 1
            else:
                existing_count += 1
                duplicates = matches.exclude(id=zone.id)
                duplicate_count += duplicates.count()
                duplicates.delete()

            kept_zone_ids.append(zone.id)

        obsolete_zones = ResidenceZone.objects.exclude(id__in=kept_zone_ids)
        deleted_obsolete_count = obsolete_zones.count()
        obsolete_zones.delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Residence zones seeded. "
                f"Created: {created_count}, Existing: {existing_count}, "
                f"Duplicates removed: {duplicate_count}, Obsolete removed: {deleted_obsolete_count}"
            )
        )

