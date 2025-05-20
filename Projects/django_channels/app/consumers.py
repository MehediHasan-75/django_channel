from channels.consumer import SyncConsumer, AsyncConsumer
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
import json
from asgiref.sync import async_to_sync

class MySyncConsumer(SyncConsumer):
    def websocket_connect(self, event):
        print('WebSocket Connected...', event)
        async_to_sync(self.channel_layer.group_add)(
            "broadcast_group",
            self.channel_name
        )
        self.send({
            "type": "websocket.accept"
        })

    def websocket_receive(self, event):
        print("Message Received...", event)
        text_data = event.get('text', '')
        if text_data:
            try:
                data = json.loads(text_data)
                print("Received data:", data)
            except json.JSONDecodeError:
                print("Invalid JSON received:", text_data)

    def websocket_disconnect(self, event):
        print('WebSocket Disconnected...', event)
        async_to_sync(self.channel_layer.group_discard)(
            "broadcast_group",
            self.channel_name
        )
        raise StopConsumer()

    def broadcast_message(self, event):
        print("Broadcasting message to client:", event['message'])
        self.send({
            "type": "websocket.send",
            "text": json.dumps({
                "message": event['message'],
                "command": "send_data"
            })
        })

class MyAsyncConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('WebSocket Connected...')
        # Join a group
        print('channle layer', self.channel_layer)
        print('get channle name', self.channel_name)
        await self.channel_layer.group_add("broadcast_group", self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "greeting",
            "message": "Hello! the server is connected"
        }))

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard("broadcast_group", self.channel_name)
        print('WebSocket Disconnected...', close_code)

    async def receive(self, text_data=None, bytes_data=None):
        print("Receive triggered:", text_data)
        if text_data:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            sender = text_data_json.get('sender', '')

            if sender == "server":
                print("Ignored server-originated message.")
                return  # Don't rebroadcast

            print("Broadcasting to group...")
            await self.channel_layer.group_send(
                "broadcast_group",
                {
                    "type": "broadcast.message",
                    "message": message,
                    "sender": "server"
                }
            )

    async def broadcast_message(self, event):  # Make this method async
        print("Broadcasting message to client:", event['message'])
        await self.send(text_data=json.dumps({
            "message": event['message'],
            "command": "send_data",
            "sender": "server"
        }))