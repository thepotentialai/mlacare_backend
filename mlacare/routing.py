from django.urls import re_path

from matching.consumers import AgentConsumer, PatientConsumer

websocket_urlpatterns = [
    re_path(r'^ws/agents/(?P<agent_id>\d+)/$', AgentConsumer.as_asgi()),
    re_path(r'^ws/patients/(?P<patient_id>\d+)/$', PatientConsumer.as_asgi()),
]
