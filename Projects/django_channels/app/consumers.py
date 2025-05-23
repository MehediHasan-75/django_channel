# from channels.consumer import SyncConsumer, AsyncConsumer
# from channels.exceptions import StopConsumer
# from channels.generic.websocket import AsyncWebsocketConsumer
# from asgiref.sync import async_to_sync
# import json

# class MySyncConsumer(SyncConsumer):
#     def websocket_connect(self, event):
#         print('WebSocket Connected...', event)
#         async_to_sync(self.channel_layer.group_add)(
#             "broadcast_group",
#             self.channel_name
#         )
#         self.send({
#             "type": "websocket.accept"
#         })

#     def websocket_receive(self, event):
#         print("Message Received...", event)
#         text_data = event.get('text', '')
#         if text_data:
#             try:
#                 data = json.loads(text_data)
#                 print("Received data:", data)

#                 is_response = data.get("is_response", False)
#                 message_id = data.get("message_id", "")
#                 message = data.get("message", "")

#                 if is_response and message_id:
#                     reply_channel = f"reply_{message_id}"
#                     async_to_sync(self.channel_layer.group_send)(
#                         reply_channel,
#                         {
#                             "type": "websocket.reply",
#                             "content": {
#                                 "consumer": "sync",
#                                 "channel_name": self.channel_name,
#                                 "message_id": message_id,
#                                 "status": "responded",
#                                 "actual_message": message
#                             }
#                         }
#                     )

#             except json.JSONDecodeError:
#                 print("Invalid JSON received:", text_data)

#     def websocket_disconnect(self, event):
#         print('WebSocket Disconnected...', event)
#         async_to_sync(self.channel_layer.group_discard)(
#             "broadcast_group",
#             self.channel_name
#         )
#         raise StopConsumer()

#     def broadcast_message(self, event):
#         print("Broadcasting message to client:", event)

#         if event.get('command') == 'request_reply' and 'reply_channel' in event:
#             message_id = event.get('message_id', 'unknown')
#             reply_channel = event.get('reply_channel')

#             # Send to client
#             self.send({
#                 "type": "websocket.send",
#                 "text": json.dumps({
#                     "message": event['message'],
#                     "command": "send_data",
#                     "requires_reply": True,
#                     "message_id": message_id
#                 })
#             })

#             # Optional immediate confirmation to script (can be removed)
#             async_to_sync(self.channel_layer.group_send)(
#                 reply_channel,
#                 {
#                     "type": "websocket.reply",
#                     "content": {
#                         "consumer": "sync",
#                         "channel_name": self.channel_name,
#                         "message_id": message_id,
#                         "status": "delivered"
#                     }
#                 }
#             )
#         else:
#             self.send({
#                 "type": "websocket.send",
#                 "text": json.dumps({
#                     "message": event['message'],
#                     "command": "send_data"
#                 })
#             })


# class MyAsyncConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.channel_layer.group_add("broadcast_group", self.channel_name)
#         await self.accept()
#         await self.send(text_data=json.dumps({
#             "type": "greeting",
#             "message": "Hello! The server is connected"
#         }))
#         print(f"[Connected] {self.channel_name}")

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard("broadcast_group", self.channel_name)
#         print(f"[Disconnected] {self.channel_name}")

#     async def receive(self, text_data=None, bytes_data=None):
#         print("Receive triggered:", text_data)
#         if text_data:
#             try:
#                 data = json.loads(text_data)
#                 message = data.get("message", "")
#                 message_id = data.get("message_id", "")
#                 is_response = data.get("is_response", False)

#                 if is_response and message_id:
#                     reply_channel = f"reply_{message_id}"
#                     await self.channel_layer.group_send(
#                         reply_channel,
#                         {
#                             "type": "websocket.reply",
#                             "content": {
#                                 "consumer": "async",
#                                 "channel_name": self.channel_name,
#                                 "message_id": message_id,
#                                 "status": "responded",
#                                 "actual_message": message
#                             }
#                         }
#                     )
#                 else:
#                     # Broadcast to other clients
#                     await self.channel_layer.group_send(
#                         "broadcast_group",
#                         {
#                             "type": "broadcast_message",
#                             "message": message
#                         }
#                     )
#             except json.JSONDecodeError:
#                 print("Invalid JSON received")

#     async def broadcast_message(self, event):
#         print("Broadcasting message to client:", event)

#         if event.get('command') == 'request_reply' and 'reply_channel' in event:
#             message_id = event.get('message_id', 'unknown')
#             reply_channel = event.get('reply_channel')

#             # Send message to client requesting reply
#             await self.send(text_data=json.dumps({
#                 "message": event['message'],
#                 "command": "send_data",
#                 "requires_reply": True,
#                 "message_id": message_id
#             }))

#         #     # Optional: confirm delivery
#         #     await self.channel_layer.group_send(
#         #         reply_channel,
#         #         {
#         #             "type": "websocket.reply",
#         #             "content": {
#         #                 "consumer": "async",
#         #                 "channel_name": self.channel_name,
#         #                 "message_id": message_id,
#         #                 "status": "delivered"
#         #             }
#         #         }
#         #     )
#         # else:
#         #     await self.send(text_data=json.dumps({
#         #         "message": event['message'],
#         #         "command": "send_data"
#         #     }))
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

                command = data.get("command", "")
                message_type = data.get("type", "")
                is_response = data.get("is_response", False)
                message_id = data.get("message_id", "")
                message = data.get("message", "")

                # Handle folder structure response from frontend
                if command == "folder_response" or message_type == "folder_response":
                    print("Folder response received from frontend")
                    reply_channel = f"folder_reply_{message_id}"
                    async_to_sync(self.channel_layer.group_send)(
                        reply_channel,
                        {
                            "type": "folder_reply",
                            "content": {
                                "message_id": message_id,
                                "status": "success",
                                "folder_structure": data.get("folder_structure", {}),
                                "path": data.get("path", ""),
                                "channel_name": self.channel_name
                            }
                        }
                    )

                # Handle folder update confirmation from frontend
                elif command == "folder_updated" or message_type == "folder_updated":
                    print("Folder update confirmation received from frontend")
                    reply_channel = f"update_reply_{message_id}"
                    async_to_sync(self.channel_layer.group_send)(
                        reply_channel,
                        {
                            "type": "update_reply",
                            "content": {
                                "message_id": message_id,
                                "status": data.get("status", "success"),
                                "message": data.get("message", "Folder updated successfully"),
                                "channel_name": self.channel_name
                            }
                        }
                    )

                # Handle regular reply responses
                elif is_response and message_id:
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

    def folder_request(self, event):
        """Handle folder read requests from MCP server"""
        print("Sending folder request to frontend:", event)
        
        self.send({
            "type": "websocket.send",
            "text": json.dumps({
                "command": "read_folder_request",
                "type": "folder_request",
                "path": event.get("path", ""),
                "message_id": event.get("message_id"),
                "message": f"Please provide folder structure for: {event.get('path', 'root')}"
            })
        })

    def folder_update(self, event):
        """Handle folder update requests from MCP server"""
        print("Sending folder update to frontend:", event)
        
        self.send({
            "type": "websocket.send",
            "text": json.dumps({
                "command": "update_folder_request",
                "type": "folder_update",
                "path": event.get("path", ""),
                "folder_structure": event.get("folder_structure", {}),
                "message_id": event.get("message_id"),
                "message": f"Please update folder: {event.get('path', 'root')}"
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
                command = data.get("command", "")
                message_type = data.get("type", "")
                message = data.get("message", "")
                message_id = data.get("message_id", "")
                is_response = data.get("is_response", False)

                # Handle folder structure response from frontend
                if command == "folder_response" or message_type == "folder_response":
                    print("Folder response received from frontend")
                    reply_channel = f"folder_reply_{message_id}"
                    await self.channel_layer.group_send(
                        reply_channel,
                        {
                            "type": "folder_reply",
                            "content": {
                                "message_id": message_id,
                                "status": "success",
                                "folder_structure": data.get("folder_structure", {}),
                                "path": data.get("path", ""),
                                "channel_name": self.channel_name
                            }
                        }
                    )

                # Handle folder update confirmation from frontend
                elif command == "folder_updated" or message_type == "folder_updated":
                    print("Folder update confirmation received from frontend")
                    reply_channel = f"update_reply_{message_id}"
                    await self.channel_layer.group_send(
                        reply_channel,
                        {
                            "type": "update_reply",
                            "content": {
                                "message_id": message_id,
                                "status": data.get("status", "success"),
                                "message": data.get("message", "Folder updated successfully"),
                                "channel_name": self.channel_name
                            }
                        }
                    )

                # Handle regular reply responses
                elif is_response and message_id:
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

    async def folder_request(self, event):
        """Handle folder read requests from MCP server"""
        print("Sending folder request to frontend:", event)
        
        await self.send(text_data=json.dumps({
            "command": "read_folder_request",
            "type": "folder_request",
            "path": event.get("path", ""),
            "message_id": event.get("message_id"),
            "message": f"Please provide folder structure for: {event.get('path', 'root')}"
        }))

    async def folder_update(self, event):
        """Handle folder update requests from MCP server"""
        print("Sending folder update to frontend:", event)
        
        await self.send(text_data=json.dumps({
            "command": "update_folder_request",
            "type": "folder_update",
            "path": event.get("path", ""),
            "folder_structure": event.get("folder_structure", {}),
            "message_id": event.get("message_id"),
            "message": f"Please update folder: {event.get('path', 'root')}"
        }))