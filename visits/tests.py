from datetime import time, timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from agents.models import AgentProfile, ResidenceZone
from patients.models import PatientProfile, Plan, Subscription
from visits.models import Visit
from visits.services import assign_agent_to_visit, generate_visits_for_subscription


class VisitAssignmentJITTests(TestCase):
    def _create_user(self, email, role):
        return User.objects.create_user(email=email, password="pass1234", role=role)

    def _create_agent(self, suffix, *, zone=None, is_available=True):
        user = self._create_user(f"agent{suffix}@test.com", "agent")
        agent = AgentProfile.objects.create(
            user=user,
            full_name=f"Agent {suffix}",
            approval_status="approved",
            is_available=is_available,
        )
        if zone is not None:
            agent.coverage_zones.add(zone)
        return agent

    def _create_patient(self, suffix, zone):
        user = self._create_user(f"patient{suffix}@test.com", "patient")
        return PatientProfile.objects.create(
            user=user,
            full_name=f"Patient {suffix}",
            city="Douala",
            address="Rue 1",
            zone=zone,
        )

    def _create_visit(self, patient, when):
        return Visit.objects.create(
            patient=patient,
            scheduled_date=when.date(),
            scheduled_time=when.time().replace(microsecond=0),
            status="pending",
            address=patient.address or "",
        )

    def test_generate_visits_for_subscription_keeps_visits_unassigned(self):
        zone = ResidenceZone.objects.create(name="Bonamoussadi", city="Douala")
        patient = self._create_patient("sub", zone)
        plan = Plan.objects.create(name="Plan A", price=1000, visits_per_month=2, is_active=True)
        subscription = Subscription.objects.create(
            patient=patient,
            plan=plan,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=30),
            status="active",
        )
        self._create_agent("sub", zone=zone, is_available=True)

        generate_visits_for_subscription(subscription)

        self.assertTrue(subscription.visits.exists())
        self.assertEqual(subscription.visits.filter(agent__isnull=False).count(), 0)

    def test_assign_agent_to_visit_prefers_same_zone_with_lowest_load(self):
        zone = ResidenceZone.objects.create(name="Akwa", city="Douala")
        patient = self._create_patient("zone", zone)
        agent_busy = self._create_agent("busy", zone=zone, is_available=True)
        agent_free = self._create_agent("free", zone=zone, is_available=True)
        other_patient = self._create_patient("other", zone)
        Visit.objects.create(
            patient=other_patient,
            agent=agent_busy,
            scheduled_date=timezone.localdate(),
            scheduled_time=time(9, 0),
            status="pending",
            address="Rue 2",
        )
        visit = self._create_visit(patient, timezone.now() + timedelta(minutes=20))

        chosen = assign_agent_to_visit(visit)
        visit.refresh_from_db()

        self.assertIsNotNone(chosen)
        self.assertEqual(visit.agent_id, agent_free.id)

    def test_assign_agent_to_visit_uses_global_fallback(self):
        zone_patient = ResidenceZone.objects.create(name="Bastos", city="Yaounde")
        zone_other = ResidenceZone.objects.create(name="Melen", city="Yaounde")
        patient = self._create_patient("fallback", zone_patient)
        fallback_agent = self._create_agent("fallback", zone=zone_other, is_available=True)
        visit = self._create_visit(patient, timezone.now() + timedelta(minutes=25))

        chosen = assign_agent_to_visit(visit)
        visit.refresh_from_db()

        self.assertIsNotNone(chosen)
        self.assertEqual(visit.agent_id, fallback_agent.id)

    def test_assign_agent_to_visit_keeps_unassigned_when_none_available(self):
        zone = ResidenceZone.objects.create(name="Nkomo", city="Yaounde")
        patient = self._create_patient("none", zone)
        self._create_agent("na", zone=zone, is_available=False)
        visit = self._create_visit(patient, timezone.now() + timedelta(minutes=15))

        chosen = assign_agent_to_visit(visit)
        visit.refresh_from_db()

        self.assertIsNone(chosen)
        self.assertIsNone(visit.agent_id)

    def test_assign_agent_to_visit_is_idempotent(self):
        zone = ResidenceZone.objects.create(name="Deido", city="Douala")
        patient = self._create_patient("idem", zone)
        first_agent = self._create_agent("idem1", zone=zone, is_available=True)
        self._create_agent("idem2", zone=zone, is_available=True)
        visit = self._create_visit(patient, timezone.now() + timedelta(minutes=10))

        chosen_first = assign_agent_to_visit(visit)
        chosen_second = assign_agent_to_visit(visit)
        visit.refresh_from_db()

        self.assertEqual(visit.agent_id, first_agent.id)
        self.assertEqual(chosen_first.id, first_agent.id)
        self.assertIsNone(chosen_second)

    def test_assign_upcoming_visits_command_assigns_only_unassigned_visits_in_window(self):
        zone = ResidenceZone.objects.create(name="Bonanjo", city="Douala")
        patient = self._create_patient("cmd", zone)
        agent = self._create_agent("cmd", zone=zone, is_available=True)
        now = timezone.now()
        upcoming = self._create_visit(patient, now + timedelta(minutes=30))
        outside_window = self._create_visit(patient, now + timedelta(hours=3))
        already_assigned = self._create_visit(patient, now + timedelta(minutes=35))
        already_assigned.agent = agent
        already_assigned.save(update_fields=["agent"])

        call_command("assign_upcoming_visits", window_minutes=60)

        upcoming.refresh_from_db()
        outside_window.refresh_from_db()
        already_assigned.refresh_from_db()
        self.assertIsNotNone(upcoming.agent_id)
        self.assertIsNone(outside_window.agent_id)
        self.assertEqual(already_assigned.agent_id, agent.id)
