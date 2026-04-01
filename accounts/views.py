import random
import string
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPVerification, User
from .serializers import (
    LoginSerializer,
    OTPVerifySerializer,
    RegisterAgentSerializer,
    RegisterPatientSerializer,
    UserSerializer,
)


def _generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def _send_otp_email(user, otp_code):
    subject = 'Vérification de votre compte MLACare'
    message = (
        f"Bonjour,\n\n"
        f"Votre code de vérification MLACare est : {otp_code}\n"
        f"Ce code est valable 10 minutes.\n\n"
        f"Si vous n'avez pas créé de compte, ignorez ce message."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


class RegisterPatientView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterPatientSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp_code = _generate_otp()
            OTPVerification.objects.create(
                user=user,
                code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(user, otp_code)
            return Response(
                {'message': 'Compte créé. Vérifiez votre email pour activer votre compte.', 'user_id': user.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterAgentView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Strip document fields from serializer payload; they are processed after account creation.
        payload = request.data.copy()
        if hasattr(payload, "setlist"):
            payload.setlist('document_types', [])
        payload.pop('document_files', None)
        payload.pop('document_types', None)

        serializer = RegisterAgentSerializer(data=payload)
        if serializer.is_valid():
            user = serializer.save()
            agent_profile = user.agent_profile

            # Accept parallel arrays from multipart: document_types[] + document_files[]
            document_types = request.data.getlist('document_types')
            document_files = request.FILES.getlist('document_files')
            if document_types and document_files:
                from agents.models import AgentDocument

                for doc_type, doc_file in zip(document_types, document_files):
                    normalized = doc_type if doc_type in {'national_id', 'diploma', 'license', 'other'} else 'other'
                    AgentDocument.objects.create(
                        agent=agent_profile,
                        document_type=normalized,
                        file=doc_file,
                    )

            otp_code = _generate_otp()
            OTPVerification.objects.create(
                user=user,
                code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(user, otp_code)
            return Response(
                {
                    'message': 'Compte agent créé. Vérifiez votre email. Votre compte sera activé après validation.',
                    'user_id': user.id,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'Le token refresh est requis.'}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Déconnexion réussie.'})
        except TokenError:
            return Response({'error': 'Token invalide ou déjà expiré.'}, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                otp = OTPVerification.objects.filter(
                    user_id=serializer.validated_data['user_id'],
                    code=serializer.validated_data['code'],
                    is_used=False,
                    expires_at__gt=timezone.now(),
                ).latest('created_at')
                otp.is_used = True
                otp.save()
                user = otp.user
                user.is_verified = True
                user.save()
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': 'Compte vérifié avec succès.',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                })
            except OTPVerification.DoesNotExist:
                return Response(
                    {'error': 'Code invalide ou expiré.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id, is_verified=False)
            otp_code = _generate_otp()
            OTPVerification.objects.create(
                user=user,
                code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(user, otp_code)
            return Response({'message': 'Nouveau code de vérification envoyé.'})
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable ou déjà vérifié.'}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': "L'email est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
            otp_code = _generate_otp()
            OTPVerification.objects.create(
                user=user,
                code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            _send_otp_email(user, otp_code)
            return Response({'message': 'Code de réinitialisation envoyé par email.', 'user_id': user.id})
        except User.DoesNotExist:
            return Response({'error': 'Aucun compte associé à cet email.'}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        code = request.data.get('code')
        new_password = request.data.get('new_password')
        if not all([user_id, code, new_password]):
            return Response(
                {'error': 'Les champs user_id, code et new_password sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response({'error': 'Le mot de passe doit contenir au moins 8 caractères.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            otp = OTPVerification.objects.filter(
                user_id=user_id,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now(),
            ).latest('created_at')
            otp.is_used = True
            otp.save()
            user = otp.user
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Mot de passe réinitialisé avec succès.'})
        except OTPVerification.DoesNotExist:
            return Response({'error': 'Code invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {'error': 'Les champs current_password et new_password sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response(
                {'error': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(current_password):
            return Response(
                {'error': 'Ancien mot de passe incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        return Response({'message': 'Mot de passe mis à jour avec succès.'})
