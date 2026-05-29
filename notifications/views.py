import json
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsPatient

from .models import Notification, SOSAlert
from .serializers import NotificationSerializer, SOSAlertSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.all()


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = request.user.notifications.get(pk=pk)
            notification.is_read = True
            notification.save()
            return Response({'message': 'Notification marquée comme lue.'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification introuvable.'}, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response({'message': f'{updated} notification(s) marquée(s) comme lues.'})


class SOSCreateView(generics.CreateAPIView):
    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated, IsPatient]

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)


class NotificationSSEView(View):
    """
    Plain Django view (not DRF APIView) so EventSource's Accept: text/event-stream
    does not trigger content negotiation 406 Not Acceptable.
    """

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        if user is None:
            raw_token = request.GET.get("access_token")
            if not raw_token:
                return JsonResponse({"detail": "Authentication required."}, status=401)
            try:
                authenticator = JWTAuthentication()
                validated_token = authenticator.get_validated_token(raw_token)
                user = authenticator.get_user(validated_token)
            except Exception:
                return JsonResponse({"detail": "Invalid token."}, status=401)

        try:
            last_id = int(request.GET.get("last_id", "0"))
        except ValueError:
            last_id = 0

        def event_stream():
            current_last_id = last_id
            while True:
                notifications = list(
                    Notification.objects.filter(user=user, id__gt=current_last_id)
                    .order_by("id")[:20]
                )
                for notification in notifications:
                    payload = {
                        "id": notification.id,
                        "title": notification.title,
                        "message": notification.message,
                        "type": notification.type,
                        "created_at": notification.created_at.isoformat(),
                    }
                    current_last_id = notification.id
                    yield f"id: {notification.id}\n"
                    yield "event: notification\n"
                    yield f"data: {json.dumps(payload)}\n\n"
                yield "event: ping\ndata: {}\n\n"
                time.sleep(2)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
