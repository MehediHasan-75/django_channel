from channels.consumer import SyncConsumer, AsyncConsumer
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
import json

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

                is_response = data.get("is_response", False)
                message_id = data.get("message_id", "")
                message = data.get("message", "")

                if is_response and message_id:
                    reply_channel = f"reply_{message_id}"
                    async_to_sync(self.channel_layer.group_send)(
                        reply_channel,
                        {
                            "type": "websocket.reply",
                            "content": {
                                "consumer": "sync",
                                "channel_name": self.channel_name,
                                "message_id": message_id,
                                "status": "responded",
                                "actual_message": message
                            }
                        }
                    )

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

        if event.get('command') == 'request_reply' and 'reply_channel' in event:
            message_id = event.get('message_id', 'unknown')
            reply_channel = event.get('reply_channel')

            # Send to client
            self.send({
                "type": "websocket.send",
                "text": json.dumps({
                    "message": event['message'],
                    "command": "send_data",
                    "requires_reply": True,
                    "message_id": message_id
                })
            })

            # Optional immediate confirmation to script (can be removed)
            async_to_sync(self.channel_layer.group_send)(
                reply_channel,
                {
                    "type": "websocket.reply",
                    "content": {
                        "consumer": "sync",
                        "channel_name": self.channel_name,
                        "message_id": message_id,
                        "status": "delivered"
                    }
                }
            )
        else:
            self.send({
                "type": "websocket.send",
                "text": json.dumps({
                    "message": event['message'],
                    "command": "send_data"
                })
            })


class MyAsyncConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("broadcast_group", self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "greeting",
            "message": "Hello! The server is connected"
        }))
        print(f"[Connected] {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("broadcast_group", self.channel_name)
        print(f"[Disconnected] {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        print("Receive triggered:", text_data)
        if text_data:
            try:
                data = json.loads(text_data)
                message = data.get("message", "")
                message_id = data.get("message_id", "")
                is_response = data.get("is_response", False)

                if is_response and message_id:
                    reply_channel = f"reply_{message_id}"
                    await self.channel_layer.group_send(
                        reply_channel,
                        {
                            "type": "websocket.reply",
                            "content": {
                                "consumer": "async",
                                "channel_name": self.channel_name,
                                "message_id": message_id,
                                "status": "responded",
                                "actual_message": message
                            }
                        }
                    )
                else:
                    # Broadcast to other clients
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

        if event.get('command') == 'request_reply' and 'reply_channel' in event:
            message_id = event.get('message_id', 'unknown')
            reply_channel = event.get('reply_channel')

            # Send message to client requesting reply
            await self.send(text_data=json.dumps({
                "message": event['message'],
                "command": "send_data",
                "requires_reply": True,
                "message_id": message_id
            }))

        #     # Optional: confirm delivery
        #     await self.channel_layer.group_send(
        #         reply_channel,
        #         {
        #             "type": "websocket.reply",
        #             "content": {
        #                 "consumer": "async",
        #                 "channel_name": self.channel_name,
        #                 "message_id": message_id,
        #                 "status": "delivered"
        #             }
        #         }
        #     )
        # else:
        #     await self.send(text_data=json.dumps({
        #         "message": event['message'],
        #         "command": "send_data"
        #     }))
