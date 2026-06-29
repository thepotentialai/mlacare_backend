from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from agents.emails import REJECTION_TYPE_DEFINITIVE, REJECTION_TYPE_REVISION
from agents.models import AgentProfile, ResidenceZone


class AgentRejectionWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='pass1234',
            role='admin',
        )
        self.agent_user = User.objects.create_user(
            email='agent@test.com',
            password='pass1234',
            role='agent',
        )
        self.zone = ResidenceZone.objects.create(name='Akwa', city='Douala')
        self.agent = AgentProfile.objects.create(
            user=self.agent_user,
            last_name='Test Agent',
            approval_status='pending',
            is_available=True,
        )
        self.agent.pending_residence_zone = self.zone
        self.agent.save(update_fields=['pending_residence_zone'])
        self.agent.pending_coverage_zones.set([self.zone])

    def _reject_url(self, agent_id=None):
        return reverse('admin-agent-reject', kwargs={'pk': agent_id or self.agent.pk})

    def _approve_url(self, agent_id=None):
        return reverse('admin-agent-approve', kwargs={'pk': agent_id or self.agent.pk})

    @patch('agents.approval.send_agent_rejection_email_safe', return_value=True)
    def test_reject_without_reason_returns_400(self, _mock_email):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self._reject_url(), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('agents.approval.send_agent_rejection_email_safe', return_value=True)
    def test_reject_pending_agent_definitively(self, mock_email):
        self.client.force_authenticate(user=self.admin)
        reason = 'Documents incomplets ou non conformes.'
        response = self.client.post(
            self._reject_url(),
            {'reason': reason, 'rejection_type': REJECTION_TYPE_DEFINITIVE},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.approval_status, 'rejected')
        self.assertEqual(self.agent.rejection_reason, reason)
        self.assertFalse(self.agent.is_available)
        self.assertIsNotNone(self.agent.rejected_at)
        self.assertEqual(self.agent.rejected_by_id, self.admin.id)
        self.assertIsNone(self.agent.pending_residence_zone_id)
        self.assertEqual(self.agent.pending_coverage_zones.count(), 0)
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args.kwargs['rejection_type'], REJECTION_TYPE_DEFINITIVE)

    @patch('agents.approval.send_agent_rejection_email_safe', return_value=True)
    def test_reject_pending_agent_with_revision_required(self, mock_email):
        self.client.force_authenticate(user=self.admin)
        reason = 'Merci de fournir un diplôme lisible et à jour.'
        response = self.client.post(
            self._reject_url(),
            {'reason': reason, 'rejection_type': REJECTION_TYPE_REVISION},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.approval_status, 'revision_required')
        self.assertEqual(self.agent.rejection_reason, reason)
        self.assertFalse(self.agent.is_available)
        self.assertIsNotNone(self.agent.pending_residence_zone_id)
        self.assertEqual(self.agent.pending_coverage_zones.count(), 1)
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args.kwargs['rejection_type'], REJECTION_TYPE_REVISION)

    @patch('agents.approval.send_agent_rejection_email_safe', return_value=True)
    def test_reject_already_decided_returns_400(self, _mock_email):
        self.agent.approval_status = 'revision_required'
        self.agent.save(update_fields=['approval_status'])
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self._reject_url(),
            {'reason': 'Motif déjà rejeté pour test.', 'rejection_type': REJECTION_TYPE_DEFINITIVE},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('agents.approval.send_agent_rejection_email_safe', return_value=True)
    def test_reapprove_rejected_agent(self, _mock_email):
        self.agent.approval_status = 'rejected'
        self.agent.rejection_reason = 'Ancien motif de test rejet.'
        self.agent.is_available = False
        self.agent.save(update_fields=['approval_status', 'rejection_reason', 'is_available'])

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self._approve_url(), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.approval_status, 'approved')
        self.assertEqual(self.agent.rejection_reason, '')
        self.assertIsNone(self.agent.rejected_at)
        self.assertIsNone(self.agent.rejected_by_id)


class RejectedAgentAccessTests(APITestCase):
    def setUp(self):
        self.agent_user = User.objects.create_user(
            email='rejected@test.com',
            password='pass1234',
            role='agent',
        )
        self.agent = AgentProfile.objects.create(
            user=self.agent_user,
            last_name='Rejected Agent',
            approval_status='rejected',
            rejection_reason='Profil non conforme aux exigences.',
            is_available=False,
        )

    def test_rejected_agent_can_read_profile(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.get(reverse('agent-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rejection_reason'], 'Profil non conforme aux exigences.')

    def test_rejected_agent_cannot_toggle_availability(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.patch(reverse('agent-availability'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejected_agent_cannot_update_profile(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.patch(reverse('agent-profile'), {'bio': 'Updated bio'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejected_agent_cannot_list_visits(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.get('/api/visits/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RevisionRequiredAgentAccessTests(APITestCase):
    def setUp(self):
        self.agent_user = User.objects.create_user(
            email='revision@test.com',
            password='pass1234',
            role='agent',
        )
        self.agent = AgentProfile.objects.create(
            user=self.agent_user,
            last_name='Revision Agent',
            approval_status='revision_required',
            rejection_reason='Veuillez mettre à jour votre diplôme.',
            is_available=False,
        )

    def test_revision_agent_can_update_profile(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.patch(
            reverse('agent-profile'),
            {'bio': 'Profil corrigé'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bio'], 'Profil corrigé')

    def test_revision_agent_can_save_revision_notes(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.patch(
            reverse('agent-profile'),
            {'revision_notes': 'Diplôme mis à jour, voir document joint.'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['revision_notes'], 'Diplôme mis à jour, voir document joint.')
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.revision_notes, 'Diplôme mis à jour, voir document joint.')

    def test_revision_notes_persist_after_resubmit(self):
        self.agent.revision_notes = 'Réponse avant resoumission.'
        self.agent.save(update_fields=['revision_notes'])
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.post(reverse('agent-resubmit'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.revision_notes, 'Réponse avant resoumission.')

    def test_revision_agent_can_update_phone(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.patch(
            reverse('agent-profile'),
            {'phone_update': '+22890123456'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent_user.refresh_from_db()
        self.assertEqual(self.agent_user.phone, '+22890123456')

    def test_revision_agent_can_delete_own_document(self):
        from agents.models import AgentDocument

        doc = AgentDocument.objects.create(
            agent=self.agent,
            document_type='diploma',
            file='agents/documents/test-diploma.pdf',
        )
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.delete(reverse('agent-document-detail', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AgentDocument.objects.filter(pk=doc.pk).exists())

    def test_revision_agent_can_resubmit(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.post(reverse('agent-resubmit'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.approval_status, 'pending')
        self.assertEqual(self.agent.rejection_reason, '')

    def test_resubmit_notifies_admin_once(self):
        from accounts.models import User
        from notifications.models import Notification
        from notifications.services import AGENT_RESUBMIT_TITLE

        admin = User.objects.create_user(
            email='admin-resubmit@test.com',
            password='pass1234',
            role='admin',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.agent_user)

        response = self.client.post(reverse('agent-resubmit'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alerts = Notification.objects.filter(user=admin, title=AGENT_RESUBMIT_TITLE)
        self.assertEqual(alerts.count(), 1)
        self.assertIn(f'[agent_id={self.agent.id}]', alerts.first().message)

        self.agent.approval_status = 'revision_required'
        self.agent.save(update_fields=['approval_status'])
        response = self.client.post(reverse('agent-resubmit'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Notification.objects.filter(user=admin, title=AGENT_RESUBMIT_TITLE).count(),
            1,
        )

    def test_revision_agent_can_replace_document_without_duplicate(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from agents.models import AgentDocument

        existing = AgentDocument.objects.create(
            agent=self.agent,
            document_type='diploma',
            file='agents/documents/old-diploma.pdf',
        )
        self.client.force_authenticate(user=self.agent_user)
        upload = SimpleUploadedFile('new-diploma.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.post(
            reverse('agent-documents'),
            {'document_type': 'diploma', 'file': upload},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(AgentDocument.objects.filter(pk=existing.pk).exists())
        self.assertEqual(
            AgentDocument.objects.filter(agent=self.agent, document_type='diploma').count(),
            1,
        )

    def test_revision_agent_cannot_list_visits(self):
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.get('/api/visits/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_agent_cannot_resubmit(self):
        self.agent.approval_status = 'pending'
        self.agent.save(update_fields=['approval_status'])
        self.client.force_authenticate(user=self.agent_user)
        response = self.client.post(reverse('agent-resubmit'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
