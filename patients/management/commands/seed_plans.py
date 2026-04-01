from django.core.management.base import BaseCommand

from patients.models import Plan


DEFAULT_PLANS = [
    {
        "name": "Silver",
        "description": "Suivi de base a domicile avec accompagnement mensuel.",
        "price": "2500.00",
        "visits_per_month": 1,
        "features": [
            "1 visite par mois",
            "Support WhatsApp",
            "Rappel des medicaments",
        ],
        "is_active": True,
    },
    {
        "name": "Gold",
        "description": "Suivi renforce avec visites plus frequentes.",
        "price": "4500.00",
        "visits_per_month": 2,
        "features": [
            "2 visites par mois",
            "Support prioritaire",
            "Suivi des signes vitaux",
        ],
        "is_active": True,
    },
    {
        "name": "Platinum",
        "description": "Accompagnement premium pour suivi intensif.",
        "price": "7000.00",
        "visits_per_month": 4,
        "features": [
            "4 visites par mois",
            "Coordination medicale",
            "Rapport detaille mensuel",
        ],
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Seed default subscription plans."

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for data in DEFAULT_PLANS:
            defaults = {
                "description": data["description"],
                "price": data["price"],
                "visits_per_month": data["visits_per_month"],
                "features": data["features"],
                "is_active": data["is_active"],
            }
            _, created = Plan.objects.get_or_create(
                name=data["name"],
                defaults=defaults,
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Plans seeded. Created: {created_count}, Existing: {existing_count}"
            )
        )

