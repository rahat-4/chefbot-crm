import json

from channels.generic.websocket import AsyncWebsocketConsumer


class RealtimeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract client_uid from the URL route
        self.client_uid = self.scope["url_route"]["kwargs"]["client_uid"]
        self.group_name = f"realtime_updates_{self.client_uid}"

        # Join room group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from room group
    async def chat_message(self, event):
        data = event["data"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"data": data}))
