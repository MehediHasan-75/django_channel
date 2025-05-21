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
        print("Broadcasting message to client:", event)
        
        # Check if this is a message that requires a reply
        if event.get('command') == 'request_reply' and 'reply_channel' in event:
            message_id = event.get('message_id', 'unknown')
            reply_channel = event.get('reply_channel')
            
            # Send the original message to the client
            self.send({
                "type": "websocket.send",
                "text": json.dumps({
                    "message": event['message'],
                    "command": "send_data",
                    "requires_reply": True,
                    "message_id": message_id
                })
            })
            
            # Then send a reply back to the script
            async_to_sync(self.channel_layer.group_send)(
                reply_channel,
                {
                    "type": "websocket.reply",
                    "content": {
                        "consumer": "sync",
                        "channel_name": self.channel_name,
                        "message_id": message_id,
                        "status": "received"
                    }
                }
            )
        else:
            # Regular message without reply requirement
            self.send({
                "type": "websocket.send",
                "text": json.dumps({
                    "message": event['message'],
                    "command": "send_data"
                })
            })


class MyAsyncConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join a group
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
            try:
                text_data_json = json.loads(text_data)
                message = text_data_json.get('message', '')
                # Only process messages from client, not auto-responses
                if not text_data_json.get('is_response'):
                    await self.channel_layer.group_send(
                        "broadcast_group",
                        {
                            "type": "broadcast_message",
                            "message": message
                        }
                    )
            except json.JSONDecodeError:
                print("Invalid JSON received")

    async def broadcast_message(self, event):
        print("Broadcasting message to client:", event)
        
        # Check if this is a message that requires a reply
        if event.get('command') == 'request_reply' and 'reply_channel' in event:
            message_id = event.get('message_id', 'unknown')
            reply_channel = event.get('reply_channel')
            
            # Send the original message to the client
            await self.send(text_data=json.dumps({
                "message": event['message'],
                "command": "send_data",
                "requires_reply": True,
                "message_id": message_id,
                "is_response": True
            }))
            
            # Then send a reply back to the script
            await self.channel_layer.group_send(
                reply_channel,
                {
                    "type": "websocket.reply",
                    "content": {
                        "consumer": "async",
                        "channel_name": self.channel_name,
                        "message_id": message_id,
                        "status": "received"
                    }
                }
            )
        else:
            # Regular message without reply requirement
            await self.send(text_data=json.dumps({
                "message": event['message'],
                "command": "send_data",
                "is_response": True
            }))