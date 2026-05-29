from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from visits.models import Visit
from visits.services import assign_agent_to_visit


class Command(BaseCommand):
    help = "Assign agents just-in-time to upcoming unassigned visits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-minutes",
            type=int,
            default=60,
            help="Minutes ahead to include in assignment window (default: 60).",
        )

    def handle(self, *args, **options):
        window_minutes = max(int(options["window_minutes"]), 1)
        now = timezone.now()
        horizon = now + timedelta(minutes=window_minutes)
        local_tz = timezone.get_current_timezone()

        visits = list(
            Visit.objects.filter(
                agent__isnull=True,
                scheduled_date__range=[now.date(), horizon.date()],
            )
            .exclude(status__in=["completed", "cancelled"])
            .order_by("scheduled_date", "scheduled_time", "id")
            .select_related("patient__zone")
        )

        processed = 0
        assigned = 0
        skipped = 0
        no_agent = 0

        for visit in visits:
            scheduled_at = timezone.make_aware(
                datetime.combine(visit.scheduled_date, visit.scheduled_time),
                local_tz,
            )
            if scheduled_at < now or scheduled_at > horizon:
                continue

            processed += 1

            # assign_agent_to_visit handles its own atomic + select_for_update,
            # so concurrent command runs are safe even without an outer lock.
            agent = assign_agent_to_visit(visit)
            if agent is not None:
                assigned += 1
            else:
                visit.refresh_from_db(fields=["agent"])
                if visit.agent_id:
                    skipped += 1
                else:
                    no_agent += 1

        self.stdout.write(
            self.style.SUCCESS(
                "assign_upcoming_visits: "
                f"processed={processed} assigned={assigned} skipped={skipped} no_agent={no_agent}"
            ),
        )
