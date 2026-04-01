import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for agents — receives real-time assignment requests."""

    async def connect(self):
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.group_name = f"agent_{self.agent_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Agent {self.agent_id} connected via WebSocket")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"Agent {self.agent_id} disconnected from WebSocket (code={close_code})")

    # Called by channel layer: channel_layer.group_send(..., {"type": "assignment_notification", ...})
    async def assignment_notification(self, event):
        await self.send(text_data=json.dumps(event['message']))


class PatientConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for patients — receives real-time matching status updates."""

    async def connect(self):
        self.patient_id = self.scope['url_route']['kwargs']['patient_id']
        self.group_name = f"patient_{self.patient_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Patient {self.patient_id} connected via WebSocket")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"Patient {self.patient_id} disconnected from WebSocket (code={close_code})")

    # Called by channel layer: channel_layer.group_send(..., {"type": "assignment_update", ...})
    async def assignment_update(self, event):
        await self.send(text_data=json.dumps(event['message']))
